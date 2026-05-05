import { useState } from "react";
import { createAgent } from "../services/api";
import "./AgentBuilder.css";

const VOICES = [
  // English Voices
  { id: "aura-asteria-en", name: "Asteria", type: "Female (Warm)", emoji: "👩", lang: "English" },
  { id: "aura-luna-en", name: "Luna", type: "Female (Soft)", emoji: "🌙", lang: "English" },
  { id: "aura-stella-en", name: "Stella", type: "Female (Bright)", emoji: "⭐", lang: "English" },
  { id: "aura-athena-en", name: "Athena", type: "Female (Wise)", emoji: "🦉", lang: "English" },
  { id: "aura-hera-en", name: "Hera", type: "Female (Authoritative)", emoji: "👑", lang: "English" },
  { id: "aura-orion-en", name: "Orion", type: "Male (Deep)", emoji: "🌌", lang: "English" },
  { id: "aura-arcas-en", name: "Arcas", type: "Male (Friendly)", emoji: "🗣️", lang: "English" },
  { id: "aura-perseus-en", name: "Perseus", type: "Male (Bold)", emoji: "⚔️", lang: "English" },
  { id: "aura-angus-en", name: "Angus", type: "Male (British)", emoji: "🎩", lang: "English" },
  { id: "aura-orpheus-en", name: "Orpheus", type: "Male (Melodic)", emoji: "🎭", lang: "English" },
  { id: "aura-helios-en", name: "Helios", type: "Male (Energetic)", emoji: "☀️", lang: "English" },
  { id: "aura-zeus-en", name: "Zeus", type: "Male (Commanding)", emoji: "⚡", lang: "English" },
  // Hindi Voice (Indian Accent)
  { id: "aura-aura-hi", name: "Hindi", type: "Indian Accent", emoji: "🇮🇳", lang: "Hindi" },
];

function AgentBuilder({ onClose, onCreated }) {
  const [name, setName] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [voiceId, setVoiceId] = useState("aura-asteria-en");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const selectedVoice = VOICES.find((v) => v.id === voiceId);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim() || !systemPrompt.trim()) {
      setError("Please fill in all fields");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const agent = await createAgent({
        name: name.trim(),
        system_prompt: systemPrompt.trim(),
        voice_id: voiceId,
      });
      onCreated(agent);
      onClose();
    } catch (err) {
      setError("Failed to create agent. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="agent-builder-overlay" onClick={onClose}>
      <div className="agent-builder-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>
            <span>🤖</span> Create New Agent
          </h2>
          <button className="close-btn" onClick={onClose}>
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {error && <div className="error-message">{error}</div>}

            <div className="form-group">
              <label>Agent Name</label>
              <input
                type="text"
                placeholder="e.g., Friendly Tutor, Sarcastic Bot"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
              <p className="hint">Give your agent a memorable name</p>
            </div>

            <div className="form-group">
              <label>Personality (System Prompt)</label>
              <textarea
                placeholder="e.g., You are a friendly tutor who explains concepts simply. Be patient and encouraging..."
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                required
              />
              <p className="hint">
                Describe how your agent should behave and respond
              </p>
            </div>

            <div className="form-group">
              <label>Voice</label>
              <select
                value={voiceId}
                onChange={(e) => setVoiceId(e.target.value)}
              >
                <optgroup label="🌐 English Voices">
                  {VOICES.filter(v => v.lang === "English").map((voice) => (
                    <option key={voice.id} value={voice.id}>
                      {voice.emoji} {voice.name} - {voice.type}
                    </option>
                  ))}
                </optgroup>
                <optgroup label="🇮🇳 Indian Voice">
                  {VOICES.filter(v => v.lang === "Hindi").map((voice) => (
                    <option key={voice.id} value={voice.id}>
                      {voice.emoji} {voice.name} - {voice.type}
                    </option>
                  ))}
                </optgroup>
              </select>

              {selectedVoice && (
                <div className="voice-preview">
                  <div className="icon">{selectedVoice.emoji}</div>
                  <div className="info">
                    <div className="name">{selectedVoice.name}</div>
                    <div className="type">{selectedVoice.type}</div>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="cancel-btn" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="submit-btn" disabled={loading}>
              {loading ? "Creating..." : "Create Agent"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default AgentBuilder;
