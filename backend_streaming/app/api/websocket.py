import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langchain_core.messages import HumanMessage, AIMessage
from ..services.voice_processor import VoiceProcessor

router = APIRouter()

@router.websocket("/chat/{agent_id}")
async def websocket_endpoint(websocket: WebSocket, agent_id: str):
    # Extract session from query params
    session_id = websocket.query_params.get("session")
    language = websocket.query_params.get("language", "English")
    
    await websocket.accept()
    
    # Fetch Agent Configuration from Django
    system_prompt = "You are a helpful assistant."
    voice_id = "aura-asteria-en"
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"http://localhost:8000/api/agents/{agent_id}/")
            if resp.status_code == 200:
                data = resp.json()
                system_prompt = data.get("system_prompt", system_prompt)
                voice_id = data.get("voice_id", voice_id)
                print(f"Loaded Agent {agent_id}: {data.get('name')}")
            else:
                print(f"Failed to fetch agent {agent_id}, using defaults. Status: {resp.status_code}")
    except Exception as e:
        print(f"Error fetching agent {agent_id}: {e}")

    # Initialize processor with session
    processor = VoiceProcessor(agent_id, websocket, system_prompt, voice_id, session_id=session_id, language=language)
    
    # Load previous history for this session
    try:
        url = f"http://localhost:8000/api/messages/?agent={agent_id}&format=json"
        if session_id:
            url += f"&session={session_id}"
            
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                messages = resp.json()
                # Convert to LangChain messages
                for msg in messages:
                    if msg['role'] == 'user':
                        processor.conversation_history.append(HumanMessage(content=msg['content']))
                    elif msg['role'] == 'assistant':
                        processor.conversation_history.append(AIMessage(content=msg['content']))
                print(f"Loaded {len(messages)} past messages for context")
                
                # Send history to frontend
                await websocket.send_json({
                    "type": "history",
                    "messages": messages
                })
    except Exception as e:
        print(f"Error loading history: {e}")

    is_ready = await processor.start()
    
    if not is_ready:
        await websocket.close(code=1011)
        return

    print(f"Connection accepted for agent {agent_id}. State: {websocket.client_state}")
    try:
        while True:
            # Receive generic message (text or binary)
            # print(f"Waiting for message... State: {websocket.client_state}")
            message = await websocket.receive()
            
            if message["type"] == "websocket.disconnect":
                print(f"Client disconnected request (event) for agent {agent_id}")
                break

            if "bytes" in message:
                # Binary audio data
                data = message["bytes"]
                await processor.process_audio(data)
            elif "text" in message:
                # Text JSON data
                try:
                    import json
                    text_data = json.loads(message["text"])
                    if text_data.get("type") == "text":
                        content = text_data.get("content")
                        if content:
                            await processor.process_text(content)
                except Exception as e:
                    print(f"Error parsing text message: {e}")
                    
    except WebSocketDisconnect:
        print(f"Client disconnected for agent {agent_id}")
        await processor.stop()
    except RuntimeError as e:
        print(f"RuntimeError in WebSocket loop: {e}. State: {websocket.client_state}")
        await processor.stop()
    except Exception as e:
        print(f"Error in WebSocket loop: {e}")
        await processor.stop()
