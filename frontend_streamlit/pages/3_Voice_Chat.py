import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Voice Chat", layout="wide")

if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.warning("Please login first.")
    st.stop()

# Sidebar Logout
if st.sidebar.button("Logout"):
    st.session_state["authenticated"] = False
    st.session_state["access_token"] = None
    st.rerun()

st.markdown("# 🎙️ Voice Chat")
st.sidebar.markdown("# Voice Chat")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Configuration")
    agent_id = st.text_input("Enter Agent ID", value="1")
    connect_btn = st.button("Connect")
    disconnect_btn = st.button("Disconnect")
    
    if connect_btn:
        st.session_state['connected'] = True
    if disconnect_btn:
        st.session_state['connected'] = False

with col2:
    st.subheader("Session")
    
    if st.session_state.get('connected'):
        st.write(f"Connecting to Agent {agent_id}...")
        
        # Custom HTML/JS Component for WebSocket Audio Streaming
        html_code = f"""
        <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; padding: 20px; }}
                    #status {{ font-size: 18px; margin-bottom: 15px; }}
                    button {{ 
                        padding: 15px 30px; 
                        font-size: 16px; 
                        cursor: pointer;
                        background: #4CAF50;
                        color: white;
                        border: none;
                        border-radius: 8px;
                        margin: 5px;
                    }}
                    button:hover {{ background: #45a049; }}
                    #stopBtn {{ background: #f44336; }}
                    #stopBtn:hover {{ background: #da190b; }}
                    #log {{ 
                        margin-top: 20px; 
                        padding: 10px; 
                        background: #f5f5f5; 
                        border-radius: 5px;
                        max-height: 200px;
                        overflow-y: auto;
                        font-size: 12px;
                    }}
                </style>
            </head>
            <body>
                <div id="status">🔴 Not Connected</div>
                <button id="startBtn" onclick="startAudio()">🎤 Start Talking</button>
                <button id="stopBtn" onclick="stopAudio()">⏹️ Stop</button>
                <div id="log"></div>
                
                <script>
                    const wsUrl = "ws://localhost:8001/ws/chat/{agent_id}";
                    let ws;
                    let mediaRecorder;
                    let audioContext;
                    let audioQueue = [];
                    let isPlaying = false;
                    
                    const statusDiv = document.getElementById('status');
                    const logDiv = document.getElementById('log');
                    
                    function log(msg) {{
                        const time = new Date().toLocaleTimeString();
                        logDiv.innerHTML = `<div>[${{time}}] ${{msg}}</div>` + logDiv.innerHTML;
                    }}

                    function connect() {{
                        ws = new WebSocket(wsUrl);
                        
                        ws.onopen = () => {{
                            statusDiv.innerHTML = "🟢 Connected - Click 'Start Talking'";
                            statusDiv.style.color = "green";
                            log("WebSocket Connected");
                        }};
                        
                        ws.onmessage = async (event) => {{
                            if (event.data instanceof Blob) {{
                                log("Received audio chunk: " + event.data.size + " bytes");
                                const arrayBuffer = await event.data.arrayBuffer();
                                audioQueue.push(arrayBuffer);
                                if (!isPlaying) {{
                                    playAudioQueue();
                                }}
                            }} else {{
                                log("Server: " + event.data);
                            }}
                        }};
                        
                        ws.onclose = () => {{
                            statusDiv.innerHTML = "🔴 Disconnected";
                            statusDiv.style.color = "red";
                            log("WebSocket Closed");
                        }};
                        
                        ws.onerror = (err) => {{
                            log("WebSocket Error: " + err);
                        }};
                    }}
                    
                    async function playAudioQueue() {{
                        if (audioQueue.length === 0) {{
                            isPlaying = false;
                            return;
                        }}
                        
                        isPlaying = true;
                        
                        if (!audioContext) {{
                            audioContext = new (window.AudioContext || window.webkitAudioContext)({{ sampleRate: 24000 }});
                        }}
                        
                        const arrayBuffer = audioQueue.shift();
                        
                        // Convert linear16 PCM to Float32 for Web Audio API
                        const int16Array = new Int16Array(arrayBuffer);
                        const float32Array = new Float32Array(int16Array.length);
                        for (let i = 0; i < int16Array.length; i++) {{
                            float32Array[i] = int16Array[i] / 32768.0;
                        }}
                        
                        // Create audio buffer
                        const audioBuffer = audioContext.createBuffer(1, float32Array.length, 24000);
                        audioBuffer.getChannelData(0).set(float32Array);
                        
                        // Play the buffer
                        const source = audioContext.createBufferSource();
                        source.buffer = audioBuffer;
                        source.connect(audioContext.destination);
                        source.onended = () => {{
                            playAudioQueue();
                        }};
                        source.start();
                    }}
                    
                    async function startAudio() {{
                        try {{
                            // Resume audio context (required by browsers)
                            if (audioContext) {{
                                await audioContext.resume();
                            }} else {{
                                audioContext = new (window.AudioContext || window.webkitAudioContext)({{ sampleRate: 24000 }});
                            }}
                            
                            const stream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
                            mediaRecorder = new MediaRecorder(stream, {{ mimeType: 'audio/webm' }});
                            
                            mediaRecorder.addEventListener('dataavailable', event => {{
                                if (event.data.size > 0 && ws && ws.readyState === WebSocket.OPEN) {{
                                    ws.send(event.data);
                                }}
                            }});
                            
                            mediaRecorder.start(250);
                            statusDiv.innerHTML = "🎤 Listening... Speak now!";
                            log("Microphone started");
                        }} catch (err) {{
                            log("Error accessing mic: " + err);
                            statusDiv.innerHTML = "❌ Mic Error: " + err.message;
                        }}
                    }}
                    
                    function stopAudio() {{
                        if (mediaRecorder && mediaRecorder.state !== 'inactive') {{
                            mediaRecorder.stop();
                            mediaRecorder.stream.getTracks().forEach(track => track.stop());
                            log("Microphone stopped");
                            statusDiv.innerHTML = "🟢 Connected - Mic stopped";
                        }}
                    }}
                    
                    // Connect immediately
                    connect();
                </script>
            </body>
        </html>
        """
        
        components.html(html_code, height=450)
        
    else:
        st.write("Click 'Connect' to start a session.")


