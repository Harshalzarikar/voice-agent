import { useState, useEffect } from "react";
import { getSessions, createSession, deleteSession, getLiveKitToken } from "../services/api";
import {
  LiveKitRoom,
  RoomAudioRenderer,
  BarVisualizer,
  VoiceAssistantControlBar,
  useVoiceAssistant,
  useRoomContext,
} from "@livekit/components-react";
import { RoomEvent } from "livekit-client";
import "@livekit/components-styles";
import "./VoiceChat.css";

// A small component to show the assistant status inside the LiveKitRoom
function AssistantStatus() {
  const { state, audioTrack } = useVoiceAssistant();
  
  const getStateText = () => {
    switch (state) {
      case "connecting": return "Connecting...";
      case "listening": return "Listening...";
      case "thinking": return "Thinking...";
      case "speaking": return "Speaking...";
      case "ready": return "Ready (Say hello)";
      default: return state;
    }
  };

  return (
    <div className="assistant-status-container" style={{ textAlign: 'center', margin: '10px 0' }}>
      <div className="status-text" style={{ fontSize: '18px', fontWeight: 'bold', color: 'var(--text-secondary)', marginBottom: '10px' }}>
        {getStateText()}
      </div>
      <div style={{ height: '60px', width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <BarVisualizer state={state} barCount={7} trackRef={audioTrack} style={{ height: '40px' }} />
      </div>
    </div>
  );
}

// A new component to display real-time speech-to-text transcriptions for both user and agent
function TranscriptsView() {
  const room = useRoomContext();
  const [messages, setMessages] = useState([]);

  useEffect(() => {
    if (!room) return;
    
    // We store transcript segments in a dictionary to update them as they stream
    const transcriptMap = new Map();

    const handleTranscription = (segments, participant) => {
      setMessages(prev => {
        const newMessages = [...prev];
        
        for (const segment of segments) {
          const isAgent = participant?.isAgent || participant?.identity?.includes('agent') || !participant;
          const msgId = segment.id;
          
          const existingIdx = newMessages.findIndex(m => m.id === msgId);
          const msg = {
            id: msgId,
            text: segment.text,
            isAgent,
            isFinal: segment.final,
            name: participant?.name || (isAgent ? "Agent" : "You"),
            timestamp: Date.now()
          };

          if (existingIdx >= 0) {
            newMessages[existingIdx] = msg;
          } else {
            newMessages.push(msg);
          }
        }
        
        // Keep only the last 50 messages to prevent memory bloat
        return newMessages.sort((a, b) => a.timestamp - b.timestamp).slice(-50);
      });
    };

    room.on(RoomEvent.TranscriptionReceived, handleTranscription);
    
    return () => {
      room.off(RoomEvent.TranscriptionReceived, handleTranscription);
    };
  }, [room]);

  return (
    <div style={{ 
      flex: 1, 
      width: '100%', 
      maxWidth: '600px', 
      overflowY: 'auto', 
      padding: '20px',
      display: 'flex',
      flexDirection: 'column',
      gap: '12px'
    }}>
      {messages.length === 0 && (
        <div style={{ textAlign: 'center', color: '#888', marginTop: '20px' }}>
          Say something to start the conversation...
        </div>
      )}
      {messages.map(msg => (
        <div key={msg.id} style={{ 
          alignSelf: msg.isAgent ? 'flex-start' : 'flex-end',
          backgroundColor: msg.isAgent ? '#2c2c2e' : '#0a84ff',
          color: 'white',
          padding: '10px 16px',
          borderRadius: '18px',
          maxWidth: '80%',
          opacity: msg.isFinal ? 1 : 0.7,
          boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
          transition: 'opacity 0.2s'
        }}>
          <div style={{ fontSize: '11px', opacity: 0.6, marginBottom: '4px' }}>{msg.name}</div>
          <div style={{ fontSize: '15px', lineHeight: '1.4' }}>{msg.text}</div>
        </div>
      ))}
    </div>
  );
}

function VoiceChat({ agent, user, onBack, onLogout }) {
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [language, setLanguage] = useState("English");
  
  // LiveKit connection state
  const [lkToken, setLkToken] = useState("");
  const [lkUrl, setLkUrl] = useState("");
  const [isConnecting, setIsConnecting] = useState(false);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    loadSessions();
  }, [agent.id]);

  const loadSessions = async () => {
    try {
      const data = await getSessions(agent.id);
      setSessions(data);
      if (data.length > 0) {
        selectSession(data[0].id);
      } else {
        createNewSession();
      }
    } catch (err) {
      console.error("Failed to load sessions", err);
    }
  };

  const createNewSession = async () => {
    try {
      const newSession = await createSession(agent.id);
      setSessions(prev => [newSession, ...prev]);
      selectSession(newSession.id);
    } catch (err) {
      console.error("Failed to create session", err);
    }
  };

  const handleDeleteSession = async (sessionId) => {
    if (!window.confirm("Are you sure you want to delete this chat history?")) return;
    try {
      await deleteSession(sessionId);
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
    setCurrentSessionId(sessionId);
    // When session changes, we disconnect LiveKit
    disconnectLiveKit();
  };

  const disconnectLiveKit = () => {
    setLkToken("");
    setLkUrl("");
    setIsConnected(false);
  };

  const connectToLiveKit = async () => {
    setIsConnecting(true);
    try {
      const roomName = `room-${agent.id}-${currentSessionId}`;
      const username = user?.username || "Guest";
      
      const data = await getLiveKitToken(roomName, username);
      setLkToken(data.token);
      setLkUrl(data.url);
      setIsConnected(true);
    } catch (error) {
      console.error("LiveKit connection error:", error);
      alert("Failed to connect to Voice Assistant.");
    } finally {
      setIsConnecting(false);
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
                <span className={`status-dot ${isConnected ? 'pulse' : ''}`} style={{ backgroundColor: isConnected ? 'green' : 'gray' }}></span>
                {isConnected ? 'Online' : 'Offline'}
              </div>
            </div>
          </div>
          <div className="language-selector">
            <button className="lang-btn active">EN</button>
            <button className="lang-btn">HI</button>
          </div>
        </div>

        {/* LiveKit Interface */}
        <div className="voice-main">
          {!isConnected ? (
            <div className="chat-empty-state" style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
              <div className="icon">🎙️</div>
              <h3>Ready to speak?</h3>
              <p>Click below to connect to the agent</p>
              <button 
                onClick={connectToLiveKit} 
                disabled={isConnecting}
                style={{
                  marginTop: '20px',
                  padding: '12px 24px',
                  backgroundColor: '#4CAF50',
                  color: 'white',
                  border: 'none',
                  borderRadius: '24px',
                  fontSize: '16px',
                  cursor: 'pointer',
                  fontWeight: 'bold'
                }}
              >
                {isConnecting ? "Connecting..." : "Start Call"}
              </button>
            </div>
          ) : (
            <LiveKitRoom
              token={lkToken}
              serverUrl={lkUrl}
              connect={true}
              audio={true}
              video={false}
              onDisconnected={disconnectLiveKit}
              style={{ display: 'flex', flexDirection: 'column', height: '100%', width: '100%', alignItems: 'center', justifyContent: 'flex-start' }}
            >
              <RoomAudioRenderer />
              
              <TranscriptsView />
              
              <AssistantStatus />
              
              <div style={{ marginTop: 'auto', marginBottom: '40px' }}>
                <VoiceAssistantControlBar />
              </div>
            </LiveKitRoom>
          )}
        </div>
      </div>
    </div>
  );
}

export default VoiceChat;
