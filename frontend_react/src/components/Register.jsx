import { useState } from "react";
import { register, login } from "../services/api";
import "./Login.css";

function Register({ onLogin, onSwitchToLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    
    if (password.length < 6) {
      setError("Password must be at least 6 characters");
      return;
    }

    setLoading(true);
    setError("");

    try {
      // Register the user
      await register(username, password, email);
      
      // Auto-login after successful registration
      const data = await login(username, password);
      localStorage.setItem("token", data.access);
      onLogin(data.access, username);
    } catch (err) {
      setError(err.message || "Registration failed");
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
          Create Your <span className="gradient-text">Account</span>
        </h1>
        <p>
          Join VoiceAI to build intelligent voice agents with custom personalities.
          Get started in seconds.
        </p>
        <div className="login-features">
          <div className="login-feature">
            <div className="icon">✨</div>
            <span>Free to start, no credit card required</span>
          </div>
          <div className="login-feature">
            <div className="icon">🔒</div>
            <span>Secure authentication with JWT</span>
          </div>
          <div className="login-feature">
            <div className="icon">🚀</div>
            <span>Create unlimited voice agents</span>
          </div>
        </div>
      </div>

      {/* Registration Form */}
      <div className="login-form-container">
        <div className="login-card fade-in">
          <h2>Create Account</h2>
          <p className="subtitle">Sign up to start building voice agents</p>

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label>Username</label>
              <input
                type="text"
                placeholder="Choose a username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label>Email (optional)</label>
              <input
                type="email"
                placeholder="your@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label>Password</label>
              <input
                type="password"
                placeholder="At least 6 characters"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label>Confirm Password</label>
              <input
                type="password"
                placeholder="Confirm your password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
              />
            </div>

            {error && <div className="error-message">{error}</div>}

            <button type="submit" className="submit-btn" disabled={loading}>
              {loading ? "Creating Account..." : "Create Account"}
            </button>
          </form>

          <div className="auth-switch">
            Already have an account?{" "}
            <button type="button" onClick={onSwitchToLogin}>
              Sign In
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Register;
