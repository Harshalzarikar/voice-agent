import { useState, useRef, useEffect } from "react";
import { getWebSocketUrl } from "../services/api";
import "./VoiceChat.css";

function VoiceChat({ agent, user, onBack, onLogout }) {
  const [status, setStatus] = useState("connecting");
  const [isListening, setIsListening] = useState(false);
  const [logs, setLogs] = useState([]);
  const [showTranscript, setShowTranscript] = useState(true);
  
  const wsRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioContextRef = useRef(null);
  const audioQueueRef = useRef([]);
  const isPlayingRef = useRef(false);

  const addLog = (msg) => {
    const time = new Date().toLocaleTimeString();
    setLogs((prev) => [{ time, msg }, ...prev.slice(0, 30)]);
  };

  useEffect(() => {
    const ws = new WebSocket(getWebSocketUrl(agent.id));
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("connected");
      addLog("Connected to voice server");
    };

    ws.onmessage = async (event) => {
      if (event.data instanceof Blob) {
        const arrayBuffer = await event.data.arrayBuffer();
        audioQueueRef.current.push(arrayBuffer);
        if (!isPlayingRef.current) {
          playAudioQueue();
        }
      } else {
        addLog(`${event.data}`);
      }
    };

    ws.onclose = () => {
      setStatus("disconnected");
      addLog("Connection closed");
    };

    ws.onerror = () => {
      addLog("Connection error");
    };

    return () => {
      ws.close();
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        mediaRecorderRef.current.stop();
      }
    };
  }, [agent.id]);

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
    source.onended = playAudioQueue;
    source.start();
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
      addLog("Microphone activated - speak now");
    } catch (err) {
      addLog(`Microphone error: ${err.message}`);
    }
  };

  const stopListening = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach((track) => track.stop());
      setIsListening(false);
      setStatus("connected");
      addLog("Microphone stopped");
    }
  };

  const getStatusText = () => {
    switch (status) {
      case "connecting": return "Connecting...";
      case "connected": return "Ready";
      case "listening": return "Listening...";
      case "disconnected": return "Disconnected";
      default: return status;
    }
  };

  return (
    <div className="voice-chat-page">
      {/* Header */}
      <div className="voice-header">
        <div className="voice-header-left">
          <button className="back-button" onClick={onBack}>
            ← Back
          </button>
          <div className="agent-info">
            <div className="avatar">🤖</div>
            <div className="details">
              <h2>{agent.name}</h2>
              <div className={`status ${status}`}>
                <span className={`status-dot ${isListening ? 'pulse' : ''}`}></span>
                {getStatusText()}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="voice-main">
        {status === "connecting" ? (
          <div className="connecting-state">
            <div className="connecting-spinner"></div>
            <p style={{ color: "var(--text-secondary)" }}>Connecting to {agent.name}...</p>
          </div>
        ) : (
          <>
            {/* Waveform Visualization */}
            <div className={`waveform-container ${isListening ? 'active' : ''}`}>
              <div className="waveform-ring ring-1"></div>
              <div className="waveform-ring ring-2"></div>
              <div className="waveform-ring ring-3"></div>
              <div className="waveform-ring ring-4"></div>
              
              <button
                className={`mic-button ${isListening ? 'active' : 'inactive'}`}
                onClick={isListening ? stopListening : startListening}
              >
                {isListening ? '⏹️' : '🎤'}
              </button>
            </div>

            {/* Instructions */}
            <div className="voice-instructions">
              <h3>{isListening ? "I'm listening..." : "Tap to speak"}</h3>
              <p>
                {isListening
                  ? "Speak naturally. I'll respond when you pause."
                  : `Click the microphone to start talking with ${agent.name}`}
              </p>
            </div>

            {/* Controls */}
            <div className="voice-controls">
              <button
                className="control-btn"
                onClick={() => setShowTranscript(!showTranscript)}
              >
                {showTranscript ? "Hide" : "Show"} Transcript
              </button>
            </div>
          </>
        )}

        {/* Transcript Panel */}
        {showTranscript && logs.length > 0 && (
          <div className="transcript-panel">
            <div className="transcript-header">
              <h4>Activity Log</h4>
              <button onClick={() => setLogs([])}>Clear</button>
            </div>
            <div className="transcript-content">
              {logs.map((log, i) => (
                <div key={i} className="transcript-entry">
                  <span className="time">{log.time}</span>
                  {log.msg}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default VoiceChat;
