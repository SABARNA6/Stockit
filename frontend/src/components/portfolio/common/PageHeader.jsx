import { Icon } from "../utils";

export default function PageHeader({ iconKey, title, sub, action }) {
  const icon = Icon[iconKey];
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "flex-start",
        marginBottom: 24,
        flexWrap: "wrap",
        gap: 12,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <div
          style={{
            width: 38,
            height: 38,
            background: "var(--green-bg)",
            border: "1px solid var(--green)",
            borderRadius: 8,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "var(--green)",
          }}
        >
          {icon}
        </div>
        <div>
          <h1
            style={{
              fontFamily: "var(--sans)",
              fontSize: 20,
              fontWeight: 700,
              color: "var(--text-primary)",
              lineHeight: 1,
            }}
          >
            {title}
          </h1>
          {sub && (
            <p
              style={{
                fontSize: 12,
                color: "var(--text-muted)",
                fontFamily: "var(--mono)",
                marginTop: 4,
              }}
            >
              {sub}
            </p>
          )}
        </div>
      </div>
      {action}
    </div>
  );
}
