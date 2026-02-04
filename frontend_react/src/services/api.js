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
  if (response.status === 401) throw new Error("401 Unauthorized");
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
  if (response.status === 401) throw new Error("401 Unauthorized");
  if (!response.ok) throw new Error("Failed to create agent");
  return response.json();
};

export const getSessions = async (token, agentId) => {
  const response = await fetch(`${API_BASE}/api/sessions/?agent=${agentId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new Error("Failed to fetch sessions");
  return response.json();
};

export const createSession = async (token, agentId) => {
  const response = await fetch(`${API_BASE}/api/sessions/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ agent: agentId }),
  });
  if (!response.ok) throw new Error("Failed to create session");
  return response.json();
};

export const deleteSession = async (token, sessionId) => {
  const response = await fetch(`${API_BASE}/api/sessions/${sessionId}/`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new Error("Failed to delete session");
  return true;
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

export const getWebSocketUrl = (agentId, token, sessionId) => {
  let url = `${WS_BASE}/ws/chat/${agentId}?token=${token}`;
  if (sessionId) {
    url += `&session=${sessionId}`;
  }
  return url;
};
