export default function ThemeToggle({ theme, onToggle }) {
  const isDark = theme === "dark";

  return (
    <button
      className="theme-toggle"
      onClick={onToggle}
      aria-label={`Switch to ${isDark ? "light" : "dark"} mode`}
      title={`Switch to ${isDark ? "light" : "dark"} mode`}
    >
      {/* Icon */}
      <span className="tt-icon" aria-hidden="true">
        {isDark ? "🌙" : "☀️"}
      </span>

      {/* Sliding pill */}
      <div className="tt-track">
        <div className="tt-knob" />
      </div>

      {/* Label */}
      <span className="tt-label">{isDark ? "Dark" : "Light"}</span>
    </button>
  );
}
