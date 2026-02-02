import { useState, useEffect } from "react";
import Login from "./components/Login";
import Register from "./components/Register";
import Dashboard from "./components/Dashboard";
import VoiceChat from "./components/VoiceChat";
import "./App.css";

function App() {
  const [token, setToken] = useState(null);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [user, setUser] = useState(null);
  const [authView, setAuthView] = useState("login"); // "login" or "register"

  useEffect(() => {
    const savedToken = localStorage.getItem("token");
    const savedUser = localStorage.getItem("user");
    if (savedToken) {
      setToken(savedToken);
      if (savedUser) setUser(JSON.parse(savedUser));
    }
  }, []);

  const handleLogin = (accessToken, username) => {
    setToken(accessToken);
    setUser({ username });
    localStorage.setItem("user", JSON.stringify({ username }));
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    setToken(null);
    setUser(null);
    setSelectedAgent(null);
  };

  if (!token) {
    if (authView === "register") {
      return (
        <Register
          onLogin={handleLogin}
          onSwitchToLogin={() => setAuthView("login")}
        />
      );
    }
    return (
      <Login
        onLogin={handleLogin}
        onSwitchToRegister={() => setAuthView("register")}
      />
    );
  }

  if (selectedAgent) {
    return (
      <VoiceChat
        agent={selectedAgent}
        user={user}
        onBack={() => setSelectedAgent(null)}
        onLogout={handleLogout}
      />
    );
  }

  return (
    <Dashboard
      token={token}
      user={user}
      onSelectAgent={setSelectedAgent}
      onLogout={handleLogout}
    />
  );
}

export default App;
