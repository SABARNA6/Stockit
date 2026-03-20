export default function StatCard({ label, value, sub, color, delay = "0s" }) {
  return (
    <div
      style={{
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
        borderRadius: 10,
        padding: "16px 18px",
        flex: 1,
        minWidth: 120,
        animation: `fadeUp .4s ease both`,
        animationDelay: delay,
      }}
    >
      <div
        style={{
          fontSize: 9,
          letterSpacing: "0.18em",
          color: "var(--text-muted)",
          fontFamily: "var(--mono)",
          textTransform: "uppercase",
          marginBottom: 8,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: 20,
          fontWeight: 700,
          color: color || "var(--text-primary)",
          fontFamily: "var(--mono)",
          lineHeight: 1,
        }}
      >
        {value}
      </div>
      {sub && (
        <div
          style={{
            fontSize: 10,
            color: "var(--text-muted)",
            marginTop: 4,
            fontFamily: "var(--mono)",
          }}
        >
          {sub}
        </div>
      )}
    </div>
  );
}
