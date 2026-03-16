import { useState } from "react";
import { useAuth } from "./context/AuthContext";

// ─── Input Field ──────────────────────────────────────────────────────────────
function Field({ label, type = "text", value, onChange, placeholder, error }) {
  const [show, setShow] = useState(false);
  const isPassword = type === "password";
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <label
        style={{
          fontSize: 10,
          letterSpacing: "0.15em",
          color: "var(--text-muted)",
          fontFamily: "var(--mono)",
          textTransform: "uppercase",
        }}
      >
        {label}
      </label>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          background: "var(--bg-elevated)",
          border: `1px solid ${error ? "var(--red)" : "var(--border)"}`,
          borderRadius: 8,
          overflow: "hidden",
          transition: "border-color .15s",
        }}
      >
        <input
          type={isPassword && !show ? "password" : "text"}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          style={{
            flex: 1,
            background: "transparent",
            border: "none",
            outline: "none",
            color: "var(--text-primary)",
            fontFamily: "var(--mono)",
            fontSize: 13,
            padding: "11px 14px",
          }}
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setShow((s) => !s)}
            style={{
              background: "transparent",
              border: "none",
              padding: "0 12px",
              color: "var(--text-muted)",
              cursor: "pointer",
              fontSize: 12,
              fontFamily: "var(--mono)",
            }}
          >
            {show ? "HIDE" : "SHOW"}
          </button>
        )}
      </div>
      {error && (
        <span
          style={{
            fontSize: 11,
            color: "var(--red)",
            fontFamily: "var(--mono)",
          }}
        >
          ⚠ {error}
        </span>
      )}
    </div>
  );
}

// ─── AuthPage ─────────────────────────────────────────────────────────────────
export default function AuthPage({ onBack }) {
  const { signIn, signUp } = useAuth();
  const [mode, setMode] = useState("login");
  const [submitting, setSubmitting] = useState(false);
  const [globalError, setGlobalError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [errors, setErrors] = useState({});

  const validate = () => {
    const e = {};
    if (mode === "signup" && !fullName.trim()) e.fullName = "Name is required";
    if (!email.trim()) e.email = "Email is required";
    else if (!/\S+@\S+\.\S+/.test(email)) e.email = "Invalid email address";
    if (!password) e.password = "Password is required";
    else if (password.length < 6) e.password = "Minimum 6 characters";
    if (mode === "signup" && password !== confirm)
      e.confirm = "Passwords do not match";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = async () => {
    setGlobalError("");
    setSuccessMsg("");
    if (!validate()) return;
    setSubmitting(true);
    try {
      if (mode === "login") {
        await signIn({ email, password });
        onBack?.();
        // signIn success → Supabase session triggers AuthContext → App re-renders
      } else {
        await signUp({ email, password, fullName });
        setSuccessMsg(
          "Account created! Check your email to confirm, then sign in.",
        );
        setMode("login");
      }
    } catch (err) {
      setGlobalError(err.message || "Something went wrong. Please try again.");
    }
    setSubmitting(false);
  };

  const switchMode = (m) => {
    setMode(m);
    setErrors({});
    setGlobalError("");
    setSuccessMsg("");
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        background: "var(--bg-primary)",
        alignItems: "center",
        justifyContent: "center",
        padding: 24,
        animation: "fadeUp .4s ease both",
      }}
    >
      {/* Brand */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          marginBottom: 40,
        }}
      >
        <span style={{ fontSize: 24, color: "var(--green)" }}>▲</span>
        <span
          style={{
            fontFamily: "var(--mono)",
            fontSize: 18,
            fontWeight: 600,
            letterSpacing: "0.12em",
            color: "var(--text-primary)",
          }}
        >
          MarketLens
        </span>
      </div>

      {/* Card */}
      <div
        style={{
          width: "100%",
          maxWidth: 420,
          background: "var(--bg-card)",
          border: "1px solid var(--border)",
          borderRadius: 16,
          overflow: "hidden",
          boxShadow: "var(--shadow)",
        }}
      >
        {/* Mode tabs */}
        <div
          style={{ display: "flex", borderBottom: "1px solid var(--border)" }}
        >
          {[
            ["login", "Sign In"],
            ["signup", "Create Account"],
          ].map(([m, label]) => (
            <button
              key={m}
              onClick={() => switchMode(m)}
              style={{
                flex: 1,
                padding: "16px 0",
                background: mode === m ? "var(--bg-elevated)" : "transparent",
                border: "none",
                borderBottom:
                  mode === m
                    ? "2px solid var(--green)"
                    : "2px solid transparent",
                color: mode === m ? "var(--text-primary)" : "var(--text-muted)",
                fontFamily: "var(--mono)",
                fontSize: 12,
                letterSpacing: "0.1em",
                cursor: "pointer",
                transition: "all .15s",
              }}
            >
              {label}
            </button>
          ))}
        </div>

        <div
          style={{
            padding: 32,
            display: "flex",
            flexDirection: "column",
            gap: 18,
          }}
        >
          {/* Benefit blurb */}
          <div
            style={{
              padding: "10px 14px",
              background: "var(--blue-bg)",
              border: "1px solid var(--blue)",
              borderRadius: 8,
              fontSize: 11,
              color: "var(--blue)",
              fontFamily: "var(--mono)",
              lineHeight: 1.7,
            }}
          >
            ✦ Sign in to save your portfolio, watchlist &amp; get personalised
            AI picks across sessions.
          </div>

          {/* Success */}
          {successMsg && (
            <div
              style={{
                padding: "10px 14px",
                background: "var(--green-bg)",
                border: "1px solid var(--green)",
                borderRadius: 8,
                fontSize: 12,
                color: "var(--green)",
                fontFamily: "var(--mono)",
                lineHeight: 1.6,
              }}
            >
              ✓ {successMsg}
            </div>
          )}

          {/* Global error */}
          {globalError && (
            <div
              style={{
                padding: "10px 14px",
                background: "var(--red-bg)",
                border: "1px solid var(--red)",
                borderRadius: 8,
                fontSize: 12,
                color: "var(--red)",
                fontFamily: "var(--mono)",
              }}
            >
              ⚠ {globalError}
            </div>
          )}

          {/* Fields */}
          {mode === "signup" && (
            <Field
              label="Full Name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Ravi Kumar"
              error={errors.fullName}
            />
          )}
          <Field
            label="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            error={errors.email}
          />
          <Field
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={mode === "signup" ? "Min. 6 characters" : "••••••••"}
            error={errors.password}
          />
          {mode === "signup" && (
            <Field
              label="Confirm Password"
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              placeholder="Re-enter password"
              error={errors.confirm}
            />
          )}

          {/* Forgot */}
          {mode === "login" && (
            <div style={{ textAlign: "right", marginTop: -8 }}>
              <span
                style={{
                  fontSize: 11,
                  color: "var(--blue)",
                  fontFamily: "var(--mono)",
                  cursor: "pointer",
                }}
                onClick={() =>
                  alert("Implement: supabase.auth.resetPasswordForEmail(email)")
                }
              >
                Forgot password?
              </span>
            </div>
          )}

          {/* Submit */}
          <button
            onClick={handleSubmit}
            disabled={submitting}
            style={{
              padding: "13px 0",
              background: "var(--green)",
              border: "none",
              borderRadius: 8,
              color: "#fff",
              fontFamily: "var(--mono)",
              fontSize: 13,
              fontWeight: 700,
              cursor: submitting ? "not-allowed" : "pointer",
              letterSpacing: "0.12em",
              opacity: submitting ? 0.7 : 1,
              transition: "opacity .2s",
            }}
          >
            {submitting
              ? mode === "login"
                ? "Signing in..."
                : "Creating account..."
              : mode === "login"
                ? "▲ Sign In"
                : "▲ Create Account"}
          </button>

          {/* Switch mode */}
          <p
            style={{
              textAlign: "center",
              fontSize: 12,
              color: "var(--text-muted)",
              fontFamily: "var(--mono)",
            }}
          >
            {mode === "login"
              ? "New to MarketLens? "
              : "Already have an account? "}
            <span
              onClick={() => switchMode(mode === "login" ? "signup" : "login")}
              style={{ color: "var(--blue)", cursor: "pointer" }}
            >
              {mode === "login" ? "Create an account" : "Sign in"}
            </span>
          </p>

          {/* ── Skip / back link ── */}
          {onBack && (
            <p style={{ textAlign: "center", margin: 0 }}>
              <span
                onClick={onBack}
                style={{
                  fontSize: 11,
                  color: "var(--text-muted)",
                  fontFamily: "var(--mono)",
                  cursor: "pointer",
                  letterSpacing: "0.08em",
                  borderBottom: "1px dashed var(--border-light)",
                  paddingBottom: 1,
                  transition: "color .15s",
                }}
                onMouseEnter={(e) =>
                  (e.currentTarget.style.color = "var(--text-secondary)")
                }
                onMouseLeave={(e) =>
                  (e.currentTarget.style.color = "var(--text-muted)")
                }
              >
                ← Continue without account
              </span>
            </p>
          )}
        </div>
      </div>

      <p
        style={{
          marginTop: 24,
          fontSize: 10,
          color: "var(--text-muted)",
          fontFamily: "var(--mono)",
          textAlign: "center",
          letterSpacing: "0.06em",
        }}
      >
        For informational purposes only. Not financial advice.
      </p>
    </div>
  );
}
