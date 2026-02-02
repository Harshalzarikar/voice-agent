import { useState } from "react";
import { login } from "../services/api";
import "./Login.css";

function Login({ onLogin, onSwitchToRegister }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const data = await login(username, password);
      localStorage.setItem("token", data.access);
      onLogin(data.access, username);
    } catch (err) {
      setError("Invalid username or password");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      {/* Branding Panel */}
      <div className="login-branding">
        <div className="logo">
          <div className="logo-icon">🎙️</div>
          <span className="logo-text">VoiceAI</span>
        </div>
        <h1>
          Build <span className="gradient-text">Intelligent</span><br />
          Voice Agents
        </h1>
        <p>
          Create custom AI personalities and have natural conversations. 
          Powered by advanced speech recognition and synthesis.
        </p>
        <div className="login-features">
          <div className="login-feature">
            <div className="icon">🧠</div>
            <span>Custom AI personalities with unique traits</span>
          </div>
          <div className="login-feature">
            <div className="icon">🎤</div>
            <span>Real-time voice conversations</span>
          </div>
          <div className="login-feature">
            <div className="icon">⚡</div>
            <span>Ultra-low latency responses</span>
          </div>
        </div>
      </div>

      {/* Login Form */}
      <div className="login-form-container">
        <div className="login-card fade-in">
          <h2>Welcome back</h2>
          <p className="subtitle">Sign in to continue to VoiceAI</p>
          
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label>Username</label>
              <input
                type="text"
                placeholder="Enter your username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label>Password</label>
              <input
                type="password"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            
            {error && <div className="error-message">{error}</div>}
            
            <button type="submit" className="submit-btn" disabled={loading}>
              {loading ? "Signing in..." : "Sign In"}
            </button>
          </form>

          <div className="auth-switch">
            Don't have an account?{" "}
            <button type="button" onClick={onSwitchToRegister}>
              Sign Up
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Login;
