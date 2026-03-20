import { Icon, NAV_ITEMS } from "../utils";

export default function Sidebar({
  active,
  onNavigate,
  onBack,
  displayName,
  avatarInitial,
  collapsed,
  onToggle,
}) {
  return (
    <aside
      style={{
        width: collapsed ? 56 : 220,
        minHeight: "100vh",
        background: "var(--bg-section)",
        borderRight: "1px solid var(--border)",
        display: "flex",
        flexDirection: "column",
        transition: "width .2s cubic-bezier(.4,0,.2,1)",
        flexShrink: 0,
        position: "sticky",
        top: 0,
        alignSelf: "flex-start",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          padding: "16px 12px",
          borderBottom: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          justifyContent: collapsed ? "center" : "space-between",
        }}
      >
        {!collapsed && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                width: 30,
                height: 30,
                borderRadius: 6,
                background: "linear-gradient(135deg,var(--blue),#8b5cf6)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontFamily: "var(--mono)",
                fontSize: 12,
                fontWeight: 700,
                color: "#fff",
                flexShrink: 0,
              }}
            >
              {avatarInitial}
            </div>
            <div style={{ overflow: "hidden" }}>
              <div
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  color: "var(--text-primary)",
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}
              >
                {displayName}
              </div>
              <div
                style={{
                  fontSize: 9,
                  color: "var(--green)",
                  fontFamily: "var(--mono)",
                  letterSpacing: "0.1em",
                }}
              >
                PORTFOLIO
              </div>
            </div>
          </div>
        )}
        <button
          onClick={onToggle}
          style={{
            background: "transparent",
            border: "none",
            color: "var(--text-muted)",
            cursor: "pointer",
            padding: 4,
            borderRadius: 4,
            display: "flex",
            flexShrink: 0,
          }}
        >
          {collapsed ? Icon.menu : Icon.close}
        </button>
      </div>
      <nav style={{ flex: 1, padding: "8px 0" }}>
        {NAV_ITEMS.map((item) => {
          const isActive = active === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              title={collapsed ? item.label : ""}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                width: "100%",
                padding: collapsed ? "12px 0" : "11px 16px",
                justifyContent: collapsed ? "center" : "flex-start",
                background: isActive ? "var(--bg-hover)" : "transparent",
                border: "none",
                borderLeft: isActive
                  ? `3px solid ${item.color}`
                  : "3px solid transparent",
                color: isActive ? item.color : "var(--text-muted)",
                fontFamily: "var(--mono)",
                fontSize: 12,
                cursor: "pointer",
                letterSpacing: "0.06em",
                transition: "all .15s",
                whiteSpace: "nowrap",
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  e.currentTarget.style.background = "var(--bg-hover)";
                  e.currentTarget.style.color = "var(--text-primary)";
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  e.currentTarget.style.background = "transparent";
                  e.currentTarget.style.color = "var(--text-muted)";
                }
              }}
            >
              <span style={{ flexShrink: 0 }}>{Icon[item.icon]}</span>
              {!collapsed && <span>{item.label}</span>}
            </button>
          );
        })}
      </nav>
      <div
        style={{ padding: "12px 8px", borderTop: "1px solid var(--border)" }}
      >
        <button
          onClick={onBack}
          title={collapsed ? "Back to Market" : ""}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            width: "100%",
            padding: collapsed ? "10px 0" : "9px 12px",
            justifyContent: collapsed ? "center" : "flex-start",
            background: "transparent",
            border: "none",
            borderRadius: 6,
            color: "var(--text-muted)",
            fontFamily: "var(--mono)",
            fontSize: 11,
            cursor: "pointer",
            letterSpacing: "0.08em",
            transition: "all .15s",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = "var(--bg-hover)";
            e.currentTarget.style.color = "var(--text-primary)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "transparent";
            e.currentTarget.style.color = "var(--text-muted)";
          }}
        >
          {Icon.back} {!collapsed && "Back to Market"}
        </button>
      </div>
    </aside>
  );
}
