const API_BASE = "http://localhost:8000";
const WS_BASE = "ws://localhost:8001";

export const login = async (username, password) => {
  const response = await fetch(`${API_BASE}/api/token/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) throw new Error("Login failed");
  return response.json();
};

export const getAgents = async (token) => {
  const response = await fetch(`${API_BASE}/api/agents/`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new Error("Failed to fetch agents");
  return response.json();
};

export const createAgent = async (token, agentData) => {
  const response = await fetch(`${API_BASE}/api/agents/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(agentData),
  });
  if (!response.ok) throw new Error("Failed to create agent");
  return response.json();
};

export const register = async (username, password, email = "") => {
  const response = await fetch(`${API_BASE}/api/register/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password, email }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Registration failed");
  return data;
};

export const getWebSocketUrl = (agentId) => `${WS_BASE}/ws/chat/${agentId}`;
