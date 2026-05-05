import "./Header.css";

function Header({ user }) {
  const getInitials = (name) => {
    return name ? name.charAt(0).toUpperCase() : "U";
  };

  return (
    <header className="header">
      <div className="header-left">
        <div className="logo-icon">🎙️</div>
        <span className="logo-text">VoiceAI</span>
      </div>
      <div className="header-right">
        <div className="user-info">
          <div className="user-avatar">{getInitials(user?.username)}</div>
          <span className="user-name">{user?.username || "Guest"}</span>
        </div>
      </div>
    </header>
  );
}

export default Header;
