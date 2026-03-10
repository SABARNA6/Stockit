export default function HealthRing({ score }) {
  const r = 38,
    circ = 2 * Math.PI * r,
    dash = (score / 100) * circ;
  const color = score >= 75 ? "#10d68e" : score >= 50 ? "#f0a030" : "#f04060";
  const label = score >= 75 ? "Healthy" : score >= 50 ? "Moderate" : "At Risk";
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 6,
      }}
    >
      <svg width={96} height={96}>
        <circle
          cx={48}
          cy={48}
          r={r}
          fill="none"
          stroke="var(--border)"
          strokeWidth={7}
        />
        <circle
          cx={48}
          cy={48}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={7}
          strokeDasharray={`${dash} ${circ}`}
          strokeLinecap="round"
          transform="rotate(-90 48 48)"
          style={{
            transition: "stroke-dasharray 1.2s cubic-bezier(.4,0,.2,1)",
          }}
        />
        <text
          x={48}
          y={44}
          textAnchor="middle"
          fill="var(--text-primary)"
          fontSize={15}
          fontFamily="var(--mono)"
          fontWeight={700}
        >
          {score}
        </text>
        <text
          x={48}
          y={58}
          textAnchor="middle"
          fill="var(--text-muted)"
          fontSize={8}
          fontFamily="var(--mono)"
        >
          /100
        </text>
      </svg>
      <span
        style={{
          fontSize: 10,
          color,
          fontFamily: "var(--mono)",
          letterSpacing: "0.1em",
          fontWeight: 600,
        }}
      >
        {label}
      </span>
    </div>
  );
}
