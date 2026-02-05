import { useState, useRef, useEffect } from "react";
import { getWebSocketUrl, getSessions, createSession, deleteSession } from "../services/api";
import "./VoiceChat.css";

function VoiceChat({ agent, user, onBack, onLogout }) {
  const [status, setStatus] = useState("connecting");
  const [isListening, setIsListening] = useState(false);
  const [messages, setMessages] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [inputText, setInputText] = useState("");
  
  const wsRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioContextRef = useRef(null);
  const audioQueueRef = useRef([]);
  const isPlayingRef = useRef(false);
  const currentAudioSourceRef = useRef(null);
  const messagesEndRef = useRef(null);

  // Load Component: Fetch Sessions -> Create New or Load Most Recent
  useEffect(() => {
    loadSessions();
  }, [agent.id]);

  const loadSessions = async () => {
    try {
      const token = localStorage.getItem("token");
      const data = await getSessions(token, agent.id);
      setSessions(data);
      
      if (data.length > 0) {
        // Load most recent session
        selectSession(data[0].id);
      } else {
        // Create first session
        createNewSession();
      }
    } catch (err) {
      console.error("Failed to load sessions", err);
    }
  };

  const createNewSession = async () => {
    try {
      const token = localStorage.getItem("token");
      const newSession = await createSession(token, agent.id);
      setSessions(prev => [newSession, ...prev]);
      selectSession(newSession.id);
    } catch (err) {
      console.error("Failed to create session", err);
    }
  };

  const handleDeleteSession = async (sessionId) => {
    if (!window.confirm("Are you sure you want to delete this chat history?")) return;
    
    try {
      const token = localStorage.getItem("token");
      await deleteSession(token, sessionId);
      
      const updatedSessions = sessions.filter(s => s.id !== sessionId);
      setSessions(updatedSessions);
      
      if (currentSessionId === sessionId) {
        if (updatedSessions.length > 0) {
          selectSession(updatedSessions[0].id);
        } else {
          createNewSession();
        }
      }
    } catch (err) {
      console.error("Failed to delete session", err);
    }
  };

  const selectSession = (sessionId) => {
    if (currentSessionId === sessionId) return;
    
    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close();
    }
    
    setMessages([]); // Clear explicit state, will load from WS history
    setCurrentSessionId(sessionId);
    connectWebSocket(sessionId);
  };

  const connectWebSocket = (sessionId) => {
    const token = localStorage.getItem("token");
    setStatus("connecting");
    
    const ws = new WebSocket(getWebSocketUrl(agent.id, token, sessionId));
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("connected");
    };

    ws.onmessage = async (event) => {
      if (event.data instanceof Blob) {
        const arrayBuffer = await event.data.arrayBuffer();
        audioQueueRef.current.push(arrayBuffer);
        if (!isPlayingRef.current) {
          playAudioQueue();
        }
      } else {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "text") {
            if (data.role === "assistant" || data.role === "user") {
               addMessage(data.content, data.role);
            }
          } else if (data.type === "history") {
             if (data.messages && data.messages.length > 0) {
                 const history = data.messages.map(msg => ({
                   text: msg.content,
                   sender: msg.role,
                   time: new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                 }));
                 setMessages(history);
             }
          } else if (data.type === "control" && data.action === "stop_audio") {
             stopAudioPlayback();
          }
        } catch (e) {
          console.error("Error parsing message", e);
        }
      }
    };

    ws.onclose = () => setStatus("disconnected");
    ws.onerror = () => setStatus("error");
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) wsRef.current.close();
      stopListening();
    };
  }, []);

  const addMessage = (text, sender) => {
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    setMessages((prev) => [...prev, { time, text, sender }]);
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendTextMessage = () => {
    if (!inputText.trim() || !wsRef.current) return;
    
    // Optimistically add user message
    addMessage(inputText, 'user');
    
    // Send to backend
    wsRef.current.send(JSON.stringify({
      type: "text",
      content: inputText
    }));
    
    setInputText("");
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      sendTextMessage();
    }
  };

  const stopAudioPlayback = () => {
    audioQueueRef.current = [];
    isPlayingRef.current = false;
    if (currentAudioSourceRef.current) {
      try {
        currentAudioSourceRef.current.stop();
      } catch (e) {
        // Ignore errors if already stopped
      }
      currentAudioSourceRef.current = null;
    }
  };

  const playAudioQueue = async () => {
    if (audioQueueRef.current.length === 0) {
      isPlayingRef.current = false;
      return;
    }
    isPlayingRef.current = true;

    if (!audioContextRef.current) {
      audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: 24000,
      });
    }

    const arrayBuffer = audioQueueRef.current.shift();
    const int16Array = new Int16Array(arrayBuffer);
    const float32Array = new Float32Array(int16Array.length);
    for (let i = 0; i < int16Array.length; i++) {
      float32Array[i] = int16Array[i] / 32768.0;
    }

    const audioBuffer = audioContextRef.current.createBuffer(1, float32Array.length, 24000);
    audioBuffer.getChannelData(0).set(float32Array);

    const source = audioContextRef.current.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioContextRef.current.destination);
    source.onended = () => {
      currentAudioSourceRef.current = null;
      playAudioQueue();
    };
    source.start();
    currentAudioSourceRef.current = source;
  };

  const startListening = async () => {
    try {
      if (audioContextRef.current) {
        await audioContextRef.current.resume();
      } else {
        audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)({
          sampleRate: 24000,
        });
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0 && wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(event.data);
        }
      };

      mediaRecorder.start(250);
      setIsListening(true);
      setStatus("listening");
    } catch (err) {
      console.error("Microphone error:", err);
    }
  };

  const stopListening = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach((track) => track.stop());
      setIsListening(false);
      setStatus("connected");
    }
  };

  const getStatusText = () => {
    switch (status) {
      case "connecting": return "Connecting...";
      case "connected": return "Online";
      case "listening": return "Listening...";
      case "disconnected": return "Disconnected";
      case "error": return "Connection Error";
      default: return status;
    }
  };

  const formatDate = (isoString) => {
    const date = new Date(isoString);
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  };

  return (
    <div className="voice-chat-page-layout">
      {/* Sidebar */}
      <div className="chat-sidebar">
        <div className="sidebar-header">
          <button className="back-button-small" onClick={onBack}>←</button>
          <h3>History</h3>
        </div>
        
        <button className="new-chat-btn-sidebar" onClick={createNewSession}>
          <span>+</span> New Chat
        </button>

        <div className="sessions-list">
          {sessions.map(session => (
            <div 
              key={session.id} 
              className={`session-item ${session.id === currentSessionId ? 'active' : ''}`}
              onClick={() => selectSession(session.id)}
            >
              <div className="session-info">
                <div className="session-title">{session.title || "New Conversation"}</div>
                <div className="session-date">{formatDate(session.created_at)}</div>
              </div>
              <button 
                className="delete-session-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  handleDeleteSession(session.id);
                }}
              >
                🗑️
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="voice-chat-main-area">
        {/* Header */}
        <div className="voice-header simple">
          <div className="agent-info">
            <div className="avatar">🤖</div>
            <div className="details">
              <h2>{agent.name}</h2>
              <div className="status">
                <span className={`status-dot ${status === 'listening' ? 'pulse' : ''}`}></span>
                {getStatusText()}
              </div>
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="voice-main">
          {status === "connecting" && messages.length === 0 ? (
            <div className="connecting-state">
              <div className="connecting-spinner"></div>
              <p style={{ color: "var(--text-secondary)" }}>Connecting to server...</p>
            </div>
          ) : (
            <>
              <div className="chat-container">
                {messages.length === 0 ? (
                  <div className="chat-empty-state">
                    <div className="icon">👋</div>
                    <h3>Start talking</h3>
                    <p>Tap the microphone below</p>
                  </div>
                ) : (
                  messages.map((msg, i) => (
                    <div key={i} className={`message ${msg.sender}`}>
                      <div className="message-content">
                        {msg.text}
                      </div>
                      <div className="message-meta">
                        {msg.time}
                      </div>
                    </div>
                  ))
                )}
                <div ref={messagesEndRef} />
              </div>

              <div className="voice-controls-container">
                <div className={`waveform-mini ${isListening ? 'active' : ''}`}>
                  <div className="bar"></div>
                  <div className="bar"></div>
                  <div className="bar"></div>
                  <div className="bar"></div>
                  <div className="bar"></div>
                </div>

                <div className="controls-row">
                  <div className="text-input-wrapper">
                    <input
                      type="text"
                      placeholder="Type a message..."
                      value={inputText}
                      onChange={(e) => setInputText(e.target.value)}
                      onKeyPress={handleKeyPress}
                      disabled={isListening}
                    />
                    <button onClick={sendTextMessage} disabled={!inputText.trim() || isListening}>
                      ➤
                    </button>
                  </div>

                  <div className={`mic-wrapper ${isListening ? 'listening' : ''}`}>
                    <div className="mic-ripple"></div>
                    <button
                      className={`mic-button ${isListening ? 'active' : ''}`}
                      onClick={isListening ? stopListening : startListening}
                    >
                      {isListening ? '⏹️' : '🎤'}
                    </button>
                  </div>
                </div>

                <div className="instruction-text">
                  {isListening ? "Listening..." : "Type or tap mic to speak"}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default VoiceChat;
