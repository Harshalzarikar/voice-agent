// Smart Defaults: Use ENV if set, otherwise use relative path (production) or localhost (local dev)
const isDev = import.meta.env.DEV;
const API_BASE = import.meta.env.VITE_API_URL || (isDev ? "http://localhost:8000" : "");
// For WebSockets, we need absolute URL. If VITE_WS_URL is missing, derive it from window.location in Prod
const getWsBase = () => {
  if (import.meta.env.VITE_WS_URL) return import.meta.env.VITE_WS_URL;
  if (isDev) return "ws://localhost:8001";
  // In production (relative), derive WS from current HTTPS/HTTP protocol
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}`;
};
const WS_BASE = getWsBase();

console.log("DEBUG: API_BASE is:", API_BASE);
console.log("DEBUG: WS_BASE is:", WS_BASE);

export const login = async (username, password) => {
  const response = await fetch(`${API_BASE}/api/token/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) throw new Error("Login failed");
  return response.json();
};

export const getAgents = async () => {
  const response = await fetch(`${API_BASE}/api/agents/`);
  if (!response.ok) throw new Error("Failed to fetch agents");
  return response.json();
};

export const createAgent = async (agentData) => {
  const response = await fetch(`${API_BASE}/api/agents/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(agentData),
  });
  if (!response.ok) throw new Error("Failed to create agent");
  return response.json();
};

export const getSessions = async (agentId) => {
  const response = await fetch(`${API_BASE}/api/sessions/?agent=${agentId}`);
  if (!response.ok) throw new Error("Failed to fetch sessions");
  return response.json();
};

export const createSession = async (agentId) => {
  const response = await fetch(`${API_BASE}/api/sessions/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ agent: agentId }),
  });
  if (!response.ok) throw new Error("Failed to create session");
  return response.json();
};

export const deleteSession = async (sessionId) => {
  const response = await fetch(`${API_BASE}/api/sessions/${sessionId}/`, {
    method: "DELETE",
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

export const getWebSocketUrl = (agentId, sessionId, language) => {
  let url = `${WS_BASE}/ws/chat/${agentId}?`;
  if (sessionId) {
    url += `session=${sessionId}&`;
  }
  if (language) {
    url += `language=${encodeURIComponent(language)}&`;
  }
  // remove trailing & or ?
  if (url.endsWith("&") || url.endsWith("?")) {
    url = url.slice(0, -1);
  }
  return url;
};
