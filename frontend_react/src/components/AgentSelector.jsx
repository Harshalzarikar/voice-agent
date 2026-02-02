import { useState, useEffect } from "react";
import { getAgents } from "../services/api";
import "./AgentSelector.css";

function AgentSelector({ token, onSelectAgent }) {
  const [agents, setAgents] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAgents = async () => {
      try {
        const data = await getAgents(token);
        setAgents(data);
        if (data.length > 0) {
          setSelectedId(data[0].id);
        }
      } catch (err) {
        console.error("Failed to load agents:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchAgents();
  }, [token]);

  const handleStart = () => {
    const agent = agents.find((a) => a.id === parseInt(selectedId));
    if (agent) {
      onSelectAgent(agent);
    }
  };

  if (loading) {
    return <div className="agent-selector loading">Loading agents...</div>;
  }

  return (
    <div className="agent-selector">
      <h2>🤖 Select an Agent</h2>
      <p>Choose who you want to talk to</p>
      <select
        value={selectedId}
        onChange={(e) => setSelectedId(e.target.value)}
      >
        {agents.map((agent) => (
          <option key={agent.id} value={agent.id}>
            {agent.name}
          </option>
        ))}
      </select>
      {agents.length === 0 && (
        <p className="no-agents">No agents found. Create one first!</p>
      )}
      <button onClick={handleStart} disabled={!selectedId}>
        Start Conversation
      </button>
    </div>
  );
}

export default AgentSelector;
