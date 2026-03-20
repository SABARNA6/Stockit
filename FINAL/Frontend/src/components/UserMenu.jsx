import { useState, useRef, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import { User, Briefcase, LogOut, ChevronDown } from "lucide-react";

// ─── UserMenu ─────────────────────────────────────────────────────────────────
export default function UserMenu({ onNavigatePortfolio }) {
  const { user, displayName, avatarInitial, signOut } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef();

  // Close on outside click
  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleSignOut = async () => {
    setOpen(false);
    await signOut();
  };

  return (
    <div ref={ref} style={{ position: "relative", flexShrink: 0 }}>
      {/* Trigger */}
      <button
        onClick={() => setOpen((o) => !o)}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "5px 10px 5px 5px",
          background: open ? "var(--bg-hover)" : "var(--bg-elevated)",
          border: "1px solid var(--border-light)",
          borderRadius: 8,
          cursor: "pointer",
          transition: "all .15s",
        }}
      >
        {/* Avatar */}
        <div
          style={{
            width: 28,
            height: 28,
            borderRadius: 6,
            background: "linear-gradient(135deg, var(--blue), var(--purple))",
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
        <span
          style={{
            fontFamily: "var(--mono)",
            fontSize: 11,
            color: "var(--text-primary)",
            maxWidth: 100,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {displayName}
        </span>
        <ChevronDown
          size={12}
          color="var(--text-muted)"
          style={{
            transition: "transform .2s",
            transform: open ? "rotate(180deg)" : "none",
          }}
        />
      </button>

      {/* Dropdown */}
      {open && (
        <div
          style={{
            position: "absolute",
            top: "calc(100% + 8px)",
            right: 0,
            width: 220,
            background: "var(--bg-elevated)",
            border: "1px solid var(--border-light)",
            borderRadius: 10,
            boxShadow: "var(--shadow)",
            overflow: "hidden",
            animation: "fadeUp .15s ease both",
            zIndex: 300,
          }}
        >
          {/* User info header */}
          <div
            style={{
              padding: "14px 16px",
              borderBottom: "1px solid var(--border)",
              background: "var(--bg-card)",
            }}
          >
            <div
              style={{
                fontSize: 13,
                fontWeight: 600,
                color: "var(--text-primary)",
                marginBottom: 2,
              }}
            >
              {displayName}
            </div>
            <div
              style={{
                fontSize: 11,
                color: "var(--text-muted)",
                fontFamily: "var(--mono)",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              {user?.email}
            </div>
          </div>

          {/* Menu items */}
          {[
            {
              icon: <Briefcase size={14} />,
              label: "My Portfolio",
              sub: "Holdings & analytics",
              color: "var(--green)",
              action: () => {
                setOpen(false);
                onNavigatePortfolio?.();
              },
            },
            // {
            //   icon: <User size={14} />,
            //   label: "Profile",
            //   sub: "Account settings",
            //   color: "var(--blue)",
            //   action: () => {
            //     setOpen(false);
            //     alert("Profile settings — wire to your /profile route");
            //   },
            // },
          ].map((item) => (
            <button
              key={item.label}
              onClick={item.action}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
                width: "100%",
                padding: "11px 16px",
                background: "transparent",
                border: "none",
                borderBottom: "1px solid var(--border)",
                cursor: "pointer",
                textAlign: "left",
                transition: "background .12s",
              }}
              onMouseEnter={(e) =>
                (e.currentTarget.style.background = "var(--bg-hover)")
              }
              onMouseLeave={(e) =>
                (e.currentTarget.style.background = "transparent")
              }
            >
              <span style={{ color: item.color }}>{item.icon}</span>
              <div>
                <div
                  style={{
                    fontSize: 12,
                    color: "var(--text-primary)",
                    fontWeight: 500,
                  }}
                >
                  {item.label}
                </div>
                <div
                  style={{
                    fontSize: 10,
                    color: "var(--text-muted)",
                    fontFamily: "var(--mono)",
                  }}
                >
                  {item.sub}
                </div>
              </div>
            </button>
          ))}

          {/* Sign out */}
          <button
            onClick={handleSignOut}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              width: "100%",
              padding: "11px 16px",
              background: "transparent",
              border: "none",
              cursor: "pointer",
              textAlign: "left",
              transition: "background .12s",
            }}
            onMouseEnter={(e) =>
              (e.currentTarget.style.background = "var(--red-bg)")
            }
            onMouseLeave={(e) =>
              (e.currentTarget.style.background = "transparent")
            }
          >
            <LogOut size={14} color="var(--red)" />
            <div>
              <div
                style={{ fontSize: 12, color: "var(--red)", fontWeight: 500 }}
              >
                Sign Out
              </div>
              <div
                style={{
                  fontSize: 10,
                  color: "var(--text-muted)",
                  fontFamily: "var(--mono)",
                }}
              >
                End your session
              </div>
            </div>
          </button>
        </div>
      )}
    </div>
  );
}
