import { useState } from "react";
import Dashboard from "./components/Dashboard";
import VoiceChat from "./components/VoiceChat";
import "./App.css";

function App() {
  const [selectedAgent, setSelectedAgent] = useState(null);
  
  // Dummy user since login is removed
  const user = { username: "Guest" };

  if (selectedAgent) {
    return (
      <VoiceChat
        agent={selectedAgent}
        user={user}
        onBack={() => setSelectedAgent(null)}
        onLogout={() => {}} // No-op since there's no auth
      />
    );
  }

  return (
    <Dashboard
      token={null}
      user={user}
      onSelectAgent={setSelectedAgent}
      onLogout={() => {}} // No-op
    />
  );
}

export default App;
