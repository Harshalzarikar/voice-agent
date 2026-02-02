import { useState, useEffect } from "react";
import Header from "./Header";
import AgentBuilder from "./AgentBuilder";
import { getAgents } from "../services/api";
import "./Dashboard.css";

const VOICE_EMOJIS = {
  "aura-asteria-en": "👩",
  "aura-luna-en": "🌙",
  "aura-stella-en": "⭐",
  "aura-athena-en": "🦉",
  "aura-hera-en": "👑",
  "aura-orion-en": "🌌",
  "aura-arcas-en": "🗣️",
  "aura-perseus-en": "⚔️",
  "aura-angus-en": "🎩",
  "aura-orpheus-en": "🎭",
  "aura-helios-en": "☀️",
  "aura-zeus-en": "⚡",
};

const AGENT_ICONS = ["🤖", "🧠", "💬", "🎯", "🚀", "✨", "🔮", "💡"];

function Dashboard({ token, user, onSelectAgent, onLogout }) {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showBuilder, setShowBuilder] = useState(false);

  const fetchAgents = async () => {
    try {
      const data = await getAgents(token);
      setAgents(data);
    } catch (err) {
      console.error("Failed to load agents:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAgents();
  }, [token]);

  const handleAgentCreated = (newAgent) => {
    setAgents((prev) => [...prev, newAgent]);
  };

  const getAgentIcon = (index) => {
    return AGENT_ICONS[index % AGENT_ICONS.length];
  };

  const getVoiceLabel = (voiceId) => {
    if (!voiceId) return "Default Voice";
    const parts = voiceId.split("-");
    return parts[1] ? parts[1].charAt(0).toUpperCase() + parts[1].slice(1) : voiceId;
  };

  return (
    <div className="dashboard">
      <Header user={user} onLogout={onLogout} />
      
      <div className="dashboard-content">
        <div className="dashboard-header fade-in">
          <h1>Welcome back, {user?.username || "User"} 👋</h1>
          <p>Select an agent to start a voice conversation</p>
        </div>

        {/* Stats */}
        <div className="stats-row fade-in">
          <div className="stat-card">
            <div className="icon">🤖</div>
            <div className="info">
              <h3>{agents.length}</h3>
              <p>Total Agents</p>
            </div>
          </div>
          <div className="stat-card">
            <div className="icon">🎤</div>
            <div className="info">
              <h3>{Object.keys(VOICE_EMOJIS).length}</h3>
              <p>Available Voices</p>
            </div>
          </div>
          <div className="stat-card">
            <div className="icon">⚡</div>
            <div className="info">
              <h3>Real-time</h3>
              <p>Voice Processing</p>
            </div>
          </div>
        </div>

        {/* Agents Section */}
        <div className="agents-section">
          <div className="section-header">
            <h2>Your Agents</h2>
            <button className="create-agent-btn" onClick={() => setShowBuilder(true)}>
              + Create Agent
            </button>
          </div>

          {loading ? (
            <div className="loading-container">
              <div className="loading-spinner"></div>
              <span>Loading agents...</span>
            </div>
          ) : agents.length === 0 ? (
            <div className="empty-state">
              <div className="icon">🤖</div>
              <h3>No agents yet</h3>
              <p>Create your first AI agent to get started</p>
              <button className="btn-primary" onClick={() => setShowBuilder(true)}>
                + Create Your First Agent
              </button>
            </div>
          ) : (
            <div className="agents-grid">
              {agents.map((agent, index) => (
                <div
                  key={agent.id}
                  className="agent-card fade-in"
                  style={{ animationDelay: `${index * 0.1}s` }}
                  onClick={() => onSelectAgent(agent)}
                >
                  <div className="agent-card-header">
                    <div className="agent-avatar">{getAgentIcon(index)}</div>
                    <div className="agent-status">
                      <span className="dot"></span>
                      Ready
                    </div>
                  </div>
                  <h3>{agent.name}</h3>
                  <p className="description">
                    {agent.system_prompt || "A helpful AI assistant ready to chat with you."}
                  </p>
                  <div className="agent-card-footer">
                    <div className="agent-voice">
                      <span>{VOICE_EMOJIS[agent.voice_id] || "🎤"}</span>
                      <span>{getVoiceLabel(agent.voice_id)}</span>
                    </div>
                    <button
                      className="start-chat-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectAgent(agent);
                      }}
                    >
                      Start Chat
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Agent Builder Modal */}
      {showBuilder && (
        <AgentBuilder
          token={token}
          onClose={() => setShowBuilder(false)}
          onCreated={handleAgentCreated}
        />
      )}
    </div>
  );
}

export default Dashboard;
