import asyncio
import json
from deepgram import AsyncDeepgramClient
from deepgram.core.events import EventType
from deepgram.extensions.types.sockets import (
    ListenV1ControlMessage,
    SpeakV1TextMessage,
    SpeakV1ControlMessage,
    ListenV1SpeechStartedEvent,
)
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, List
import httpx
import operator
import traceback
from ..core.config import settings

class AgentState(TypedDict):
    messages: Annotated[List[HumanMessage | AIMessage | SystemMessage], operator.add]
    intent: str

class VoiceProcessor:
    def __init__(self, agent_id: str, websocket, system_prompt: str, voice_id: str, token: str = None, session_id: str = None):
        self.agent_id = agent_id
        self.websocket = websocket
        self.system_prompt = system_prompt
        self.voice_id = voice_id
        self.auth_token = token
        self.session_id = session_id
        self.deepgram = AsyncDeepgramClient(api_key=settings.DEEPGRAM_API_KEY)
        
        # --- Orchestration Layer (Logic/Routing) ---
        self.router_llm = ChatOpenAI(
            temperature=0,
            model="qwen/qwen3-4b:free", # User explicitly requested this model ID
            openai_api_key=settings.OPENROUTER_API_KEY,
            openai_api_base="https://openrouter.ai/api/v1"
        )

        # --- Conversational Layer (Personality/Speed) ---
        self.llm = ChatOpenAI(
            temperature=0.7,
            model="liquid/lfm-2.5-1.2b-instruct:free",
            openai_api_key=settings.OPENROUTER_API_KEY,
            openai_api_base="https://openrouter.ai/api/v1",
            max_tokens=100
        )

        # Build LangGraph
        self.graph = self._build_graph()

        self.dg_connection = None
        self.dg_connection_ctx = None
        self.dg_tts_connection = None
        self.dg_tts_context = None
        self.stt_lock = asyncio.Lock() # Lock for STT socket
        self.tts_lock = asyncio.Lock() # Lock for TTS socket
        self.is_running = True
        
        # Conversation history for context
        self.conversation_history = []

    async def start(self):
        """Initialize Deepgram STT and TTS connections"""
        try:
            # --- STT Setup ---
            print("Connecting to Deepgram STT...")
            self.dg_connection_ctx = self.deepgram.listen.v1.connect(
                model="nova-2",
                language="en-IN",
                smart_format="true",
                endpointing=500,
            )
            self.dg_connection = await self.dg_connection_ctx.__aenter__()
            print("Connected to Deepgram STT")

            async def stop_tts():
                """Stop TTS playback and clear queues"""
                try:
                    # 1. Send clear command to Deepgram
                    if self.dg_tts_connection:
                        async with self.tts_lock:
                            await self.dg_tts_connection.send_control(SpeakV1ControlMessage(type="Clear"))
                    
                    # 2. Tell frontend to stop playing current audio
                    if self.websocket:
                        await self.websocket.send_text(json.dumps({
                            "type": "control",
                            "action": "stop_audio"
                        }))
                except Exception as e:
                    print(f"Error stopping TTS: {e}")

            def on_stt_message(result, **kwargs):
                try:
                    # Handle SpeechStarted (Barge-in / Interruption)
                    if isinstance(result, ListenV1SpeechStartedEvent) or (hasattr(result, 'type') and result.type == "SpeechStarted"):
                        print("User started speaking (SpeechStarted event)...")
                        asyncio.create_task(stop_tts())
                        return

                    if hasattr(result, 'channel'):
                        alternatives = result.channel.alternatives
                        if alternatives and len(alternatives) > 0:
                            sentence = alternatives[0].transcript
                            
                            # Interruption Logic: If speech detected, stop TTS
                            if result.speech_final or (len(sentence.strip()) > 0 and result.is_final):
                                if len(sentence.strip()) > 0:
                                    print(f"User interrupted with: {sentence}")
                                    asyncio.create_task(stop_tts())
                                    asyncio.create_task(self.process_text(sentence))
                except Exception as e:
                    print(f"Error processing STT message: {e}")

            self.dg_connection.on(EventType.MESSAGE, on_stt_message)
            self.dg_connection.on(EventType.ERROR, lambda e: print(f"Deepgram STT Error: {e}"))
            
            # Start listening loop in background
            asyncio.create_task(self.dg_connection.start_listening())
            
            # --- TTS Setup ---
            print(f"Connecting to Deepgram TTS with voice: {self.voice_id}...")
            # Direct connection without try/except fallback used previously to avoid 403
            self.dg_tts_context = self.deepgram.speak.v1.connect(
                model=self.voice_id,
                encoding="linear16",
                sample_rate=24000
            )
            self.dg_tts_connection = await self.dg_tts_context.__aenter__()
            print("Connected to Deepgram TTS")

            async def on_tts_message(result, **kwargs):
                try:
                    # Deepgram sends binary audio chunks or JSON metadata
                    if isinstance(result, (bytes, bytearray)):
                        # print(f"TTS audio chunk: {len(result)} bytes") # Reduce log spam
                        await self.websocket.send_bytes(result)
                except Exception as e:
                    print(f"Error processing TTS message: {e}")

            self.dg_tts_connection.on(EventType.MESSAGE, on_tts_message)
            self.dg_tts_connection.on(EventType.ERROR, lambda e: print(f"Deepgram TTS Error: {e}"))
            asyncio.create_task(self.dg_tts_connection.start_listening())

            # --- Start KeepAlive to prevent timeout ---
            asyncio.create_task(self._keep_alive())

            print("VoiceProcessor started successfully")
            return True
        except Exception as e:
            print(f"Error starting VoiceProcessor: {e}")
            traceback.print_exc()
            return False

    async def save_message(self, role: str, content: str):
        """Save message to backend database"""
        if not self.auth_token:
            return
            
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "agent": self.agent_id,
                    "role": role,
                    "content": content
                }
                if self.session_id:
                    payload["session"] = self.session_id
                    
                await client.post(
                    "http://localhost:8000/api/messages/",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.auth_token}"}
                )
        except Exception as e:
            print(f"Error saving message: {e}")

    async def generate_session_title(self, first_message: str):
        """Generate a short title for the session based on the first message"""
        if not self.session_id or not self.auth_token:
            return

        try:
            # Ask LLM for a title
            from langchain_core.messages import SystemMessage, HumanMessage
            prompt = "Generate a very short title (3-5 words max) for a conversation that starts with this message. Return ONLY the title, no quotes."
            response = await self.llm.ainvoke([
                SystemMessage(content=prompt),
                HumanMessage(content=first_message)
            ])
            title = response.content.strip()

            # Update Session in DB
            async with httpx.AsyncClient() as client:
                await client.patch(
                    f"http://localhost:8000/api/sessions/{self.session_id}/",
                    json={"title": title},
                    headers={"Authorization": f"Bearer {self.auth_token}"}
                )
            print(f"Updated session {self.session_id} title to: {title}")
        except Exception as e:
            print(f"Error generating title: {e}")

    async def process_audio(self, data: bytes):
        """Send audio to Deepgram for STT"""
        if self.dg_connection:
            async with self.stt_lock:
                await self.dg_connection.send_media(data)

    def _build_graph(self):
        """Build the LangGraph StateGraph"""
        workflow = StateGraph(AgentState)

        # Define Nodes
        def router_node(state):
            messages = state["messages"]
            last_message = messages[-1].content
            print(f"[Router] Analyzing: {last_message}")
            
            # Use Qwen to decide intent
            try:
                # Simple classification prompt
                system_msg = SystemMessage(content="""
                You are a Router. Analyze the user's input and classify the intent.
                Return ONLY one of the following JSON strings:
                {"intent": "end_conversation"}
                {"intent": "general_chat"}
                
                Rules:
                - "end_conversation": If user says bye, stop, exit, quit.
                - "general_chat": For everything else.
                Do not output thinking or markdown. Just the JSON.
                """)
                
                response = self.router_llm.invoke([system_msg, HumanMessage(content=last_message)])
                content = response.content.strip()
                
                # Cleanup potential Qwen thinking tags if present
                if "</think>" in content:
                    content = content.split("</think>")[-1].strip()
                    
                import json
                # Try to parse JSON
                try:
                    data = json.loads(content)
                    return {"intent": data.get("intent", "general_chat")}
                except:
                    # Fallback if JSON fails
                    if "end_conversation" in content:
                        return {"intent": "end_conversation"}
                    return {"intent": "general_chat"}
                    
            except Exception as e:
                print(f"[Router] Error: {e}, falling back to simple logic")
                import re
                text = last_message.lower()
                # Use regex to match whole words only (prevents "stopped" matching "stop")
                if re.search(r'\b(bye|goodbye|stop|exit|quit)\b', text):
                    return {"intent": "end_conversation"}
                return {"intent": "general_chat"}

        async def responder_node(state):
            """Responder node: Handles Personality & Conversation"""
            messages = state["messages"]
            
            # Build context with history (keep last 10 turns to avoid token overflow)
            history_messages = self.conversation_history[-10:]
            
            # System prompt with SHORT response instruction
            short_instruction = "\n\nIMPORTANT: Keep responses SHORT and conversational (1-2 sentences max). This is a voice conversation."
            system_msg = SystemMessage(content=self.system_prompt + short_instruction)
            
            full_messages = [system_msg] + history_messages + messages
            
            print(f"[Responder] Generating response with {len(history_messages)} history messages...")
            response = await self.llm.ainvoke(full_messages)
            return {"messages": [response]}

        # Add Nodes
        workflow.add_node("router", router_node)
        workflow.add_node("responder", responder_node)

        # Define Edges
        async def route_decision(state):
            intent = state["intent"]
            if intent == "end_conversation":
                # Send control message to stop frontend mic
                if self.websocket:
                    await self.websocket.send_text(json.dumps({
                        "type": "control",
                        "action": "stop_audio"
                    }))
                # Return a final system message so process_text doesn't just read the last user message
               
                # If we return END, the graph stops execution.
                # But we need to ensure the state has an assistant message if we want process_text to find one.
                # Alternative: Let route_decision return "responder" even for end_conversation, but tell responder to say bye?
                # Or: In process_text, check if 'messages' has a new message.
                
                return END
            return "responder"

        workflow.set_entry_point("router")
        
        # Use conditional routing based on intent
        workflow.add_conditional_edges(
            "router",
            route_decision,
            {
                END: END,
                "responder": "responder"
            }
        )
        
        workflow.add_edge("responder", END)

        return workflow.compile()

    async def process_text(self, text: str):
        """Process text dynamically using LangGraph"""
        try:
            print(f"Processing text: {text}")
            
            # Send User Text to Frontend
            await self.websocket.send_text(json.dumps({
                "type": "text",
                "role": "user",
                "content": text
            }))
            
            # Store user message in history
            self.conversation_history.append(HumanMessage(content=text))
            
            # Save user message to DB
            asyncio.create_task(self.save_message("user", text))

            # Auto-generate title if it's the first message and we have a session
            if self.session_id and len(self.conversation_history) <= 1:
                asyncio.create_task(self.generate_session_title(text))
            
            # Invoke Graph
            inputs = {"messages": [HumanMessage(content=text)], "intent": ""}
            result = await self.graph.ainvoke(inputs)
            
            # Extract Response
            messages = result["messages"]
            if not messages or isinstance(messages[-1], HumanMessage):
                # If the last message is still the HumanMessage, it means the graph didn't generate a response (Router -> END)
                response_text = "Goodbye."
            else:
                response_text = messages[-1].content
            
            # Store assistant message in history
            self.conversation_history.append(AIMessage(content=response_text))
            
            # Save assistant message to DB
            asyncio.create_task(self.save_message("assistant", response_text))
            
            print(f"Graph Response: {response_text}")
            
            # 1. Send Text to Frontend
            await self.websocket.send_text(json.dumps({
                "type": "text",
                "role": "assistant",
                "content": response_text
            }))

            # 2. TTS Generation (Deepgram)
            await self.generate_speech(response_text)
            
        except Exception as e:
            print(f"Error in process_text: {e}")

    def _sanitize_for_speech(self, text: str) -> str:
        """Remove markdown formatting so TTS reads naturally."""
        import re
        # Remove bold/italic markers: **text**, *text*, __text__, _text_
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'\*(.+?)\*', r'\1', text)
        text = re.sub(r'__(.+?)__', r'\1', text)
        text = re.sub(r'_(.+?)_', r'\1', text)
        # Remove headers: # ## ###
        text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
        # Remove markdown links: [text](url) -> text
        text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
        # Remove inline code: `code`
        text = re.sub(r'`(.+?)`', r'\1', text)
        # Remove remaining stray asterisks or underscores
        text = re.sub(r'[\*_]{1,2}', '', text)
        return text.strip()

    async def generate_speech(self, text: str):
        """Generate speech using Deepgram TTS and stream back to client"""
        try:
            if self.dg_tts_connection:
                # Remove markdown so TTS reads naturally
                clean_text = self._sanitize_for_speech(text)
                
                # Deepgram has a character limit (approx 2000). Truncate if necessary.
                safe_text = clean_text[:1800] 
                if len(clean_text) > 1800:
                    print(f"Warning: Truncating text length {len(clean_text)} to 1800 chars.")
                
                async with self.tts_lock:
                    await self.dg_tts_connection.send_text(SpeakV1TextMessage(type="Speak", text=safe_text))
                    await self.dg_tts_connection.send_control(SpeakV1ControlMessage(type="Flush"))
        except Exception as e:
            print(f"Error in generate_speech: {e}")

    async def _keep_alive(self):
        """Keep both STT and TTS connections alive"""
        while self.is_running:
            try:
                # STT KeepAlive
                if self.dg_connection:
                    try:
                        async with self.stt_lock:
                            # Verify connection is still open before sending
                            if self.is_running:
                                await self.dg_connection.send_control(ListenV1ControlMessage(type="KeepAlive"))
                    except Exception as e:
                        # Suppress "no close frame" error which is common during disconnect
                        if "no close frame" not in str(e):
                            print(f"Error in STT KeepAlive: {e}")
                        else:
                            # If connection is closed, stop running
                            print("STT Connection closed (KeepAlive check).")
                            break
                
                # TTS KeepAlive - Not supported/needed as per SpeakV1ControlMessage
                # if self.dg_tts_connection:
                #    pass 
                
                await asyncio.sleep(5) # Send more frequently (5s) for STT
            except Exception as e:
                if self.is_running:
                    print(f"Error in KeepAlive Loop: {e}")
                break

    async def stop(self):
        """Clean up resources"""
        self.is_running = False
        
        if self.dg_connection_ctx:
            await self.dg_connection_ctx.__aexit__(None, None, None)
        if self.dg_tts_context:
            await self.dg_tts_context.__aexit__(None, None, None)
