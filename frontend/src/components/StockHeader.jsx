import { useState, useEffect, useRef } from "react";
import { fmt } from "../api/stockApi";
import { supabase } from "../supabaseClient";
import { useAuth } from "../context/AuthContext";

// ─── Sparkline SVG ────────────────────────────────────────────────────────────
function Sparkline({ closes = [], positive }) {
  if (!closes.length) return null;
  const W = 140,
    H = 44;
  const min = Math.min(...closes);
  const max = Math.max(...closes);
  const range = max - min || 1;
  const pts = closes
    .map((v, i) => {
      const x = (i / (closes.length - 1)) * W;
      const y = H - ((v - min) / range) * (H - 6) - 3;
      return `${x},${y}`;
    })
    .join(" ");
  const color = positive ? "#22c55e" : "#ef4444";
  const fillPts = `0,${H} ${pts} ${W},${H}`;
  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      style={{ width: W, height: H, display: "block" }}
      preserveAspectRatio="none"
    >
      <defs>
        <linearGradient id={`sg-${positive}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.25" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon fill={`url(#sg-${positive})`} points={fillPts} />
      <polyline
        fill="none"
        stroke={color}
        strokeWidth="2"
        points={pts}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

// ─── Range Bar ────────────────────────────────────────────────────────────────
function RangeBar({ low, high, current }) {
  if (!low || !high || !current) return null;
  const pct = Math.min(
    Math.max(((current - low) / (high - low)) * 100, 0),
    100,
  );
  return (
    <div style={{ marginTop: 6 }}>
      <div
        style={{
          height: 4,
          background: "var(--border)",
          borderRadius: 2,
          position: "relative",
        }}
      >
        <div
          style={{
            position: "absolute",
            left: 0,
            width: "100%",
            height: "100%",
            background:
              "linear-gradient(90deg, var(--green), var(--amber), var(--red))",
            borderRadius: 2,
            opacity: 0.6,
          }}
        />
        <div
          style={{
            position: "absolute",
            left: `${pct}%`,
            top: "50%",
            transform: "translate(-50%,-50%)",
            width: 10,
            height: 10,
            borderRadius: "50%",
            background: "var(--text-primary)",
            boxShadow: "0 0 0 2px var(--bg-card)",
            zIndex: 1,
          }}
        />
      </div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginTop: 4,
        }}
      >
        <span
          style={{
            fontSize: 9,
            color: "var(--text-muted)",
            fontFamily: "var(--mono)",
          }}
        >
          {fmt.price(low)}
        </span>
        <span
          style={{
            fontSize: 9,
            color: "var(--text-muted)",
            fontFamily: "var(--mono)",
          }}
        >
          {fmt.price(high)}
        </span>
      </div>
    </div>
  );
}

// ─── Metric Chip ──────────────────────────────────────────────────────────────
function MetricChip({ label, value, sub, children }) {
  return (
    <div className="metric-chip">
      <div className="chip-label">{label}</div>
      {value && <div className="chip-value">{value}</div>}
      {sub && <div className="chip-sub">{sub}</div>}
      {children}
    </div>
  );
}

// ─── Toast ────────────────────────────────────────────────────────────────────
function showToast(message, type = "success") {
  const existing = document.getElementById("ml-toast");
  if (existing) existing.remove();
  const el = document.createElement("div");
  el.id = "ml-toast";
  el.textContent = message;
  Object.assign(el.style, {
    position: "fixed",
    bottom: "28px",
    right: "28px",
    zIndex: "9999",
    background: "var(--bg-elevated)",
    border: `1px solid ${type === "success" ? "var(--amber)" : "var(--red)"}`,
    color: type === "success" ? "var(--amber)" : "var(--red)",
    fontFamily: "var(--mono)",
    fontSize: "12px",
    padding: "10px 18px",
    borderRadius: "8px",
    boxShadow: "var(--shadow)",
    letterSpacing: "0.06em",
    animation: "fadeUp .3s ease both",
    pointerEvents: "none",
  });
  document.body.appendChild(el);
  setTimeout(() => el?.remove(), 3000);
}

// ─── Target Price Modal ───────────────────────────────────────────────────────
function TargetPriceModal({ symbol, currentPrice, onConfirm, onCancel }) {
  const [target, setTarget] = useState("");
  const [note, setNote] = useState("");
  const inputRef = useRef();

  // Auto-focus input when modal opens
  useEffect(() => {
    setTimeout(() => inputRef.current?.focus(), 50);
  }, []);

  // Close on Escape
  useEffect(() => {
    const handler = (e) => {
      if (e.key === "Escape") onCancel();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onCancel]);

  const upside =
    target && currentPrice
      ? (((parseFloat(target) - currentPrice) / currentPrice) * 100).toFixed(1)
      : null;

  const isAbove = upside !== null && parseFloat(upside) >= 0;

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onCancel}
        style={{
          position: "fixed",
          inset: 0,
          zIndex: 1000,
          background: "rgba(8,12,20,0.7)",
          backdropFilter: "blur(4px)",
          animation: "fadeIn .15s ease both",
        }}
      />

      {/* Modal card */}
      <div
        style={{
          position: "fixed",
          top: "50%",
          left: "50%",
          zIndex: 1001,
          transform: "translate(-50%,-50%)",
          width: "100%",
          maxWidth: 380,
          background: "var(--bg-card)",
          border: "1px solid var(--border-light)",
          borderRadius: 14,
          boxShadow: "0 24px 60px rgba(0,0,0,0.5)",
          animation: "modalIn .2s cubic-bezier(.34,1.56,.64,1) both",
          padding: 28,
          display: "flex",
          flexDirection: "column",
          gap: 18,
        }}
      >
        <style>{`
          @keyframes fadeIn  { from { opacity:0 } to { opacity:1 } }
          @keyframes modalIn { from { opacity:0; transform:translate(-50%,-46%) scale(.96) } to { opacity:1; transform:translate(-50%,-50%) scale(1) } }
        `}</style>

        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
          }}
        >
          <div>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                marginBottom: 4,
              }}
            >
              {/* Star icon */}
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="var(--amber)"
                stroke="var(--amber)"
                strokeWidth="1.5"
              >
                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
              </svg>
              <span
                style={{
                  fontFamily: "var(--sans)",
                  fontSize: 16,
                  fontWeight: 700,
                  color: "var(--text-primary)",
                }}
              >
                Add to Watchlist
              </span>
            </div>
            <span
              style={{
                fontFamily: "var(--mono)",
                fontSize: 11,
                color: "var(--text-muted)",
                letterSpacing: "0.08em",
              }}
            >
              {symbol} · CMP ₹{Number(currentPrice).toLocaleString("en-IN")}
            </span>
          </div>
          <button
            onClick={onCancel}
            style={{
              background: "transparent",
              border: "none",
              color: "var(--text-muted)",
              cursor: "pointer",
              fontSize: 20,
              lineHeight: 1,
              padding: "2px 4px",
              borderRadius: 4,
              transition: "color .15s",
            }}
            onMouseEnter={(e) =>
              (e.currentTarget.style.color = "var(--text-primary)")
            }
            onMouseLeave={(e) =>
              (e.currentTarget.style.color = "var(--text-muted)")
            }
          >
            ×
          </button>
        </div>

        {/* Target price input */}
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <label
            style={{
              fontSize: 10,
              letterSpacing: "0.15em",
              textTransform: "uppercase",
              color: "var(--text-muted)",
              fontFamily: "var(--mono)",
            }}
          >
            Target Price (₹){" "}
            <span style={{ color: "var(--text-muted)", fontWeight: 400 }}>
              — optional
            </span>
          </label>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              background: "var(--bg-elevated)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              overflow: "hidden",
              transition: "border-color .15s",
            }}
            onFocusCapture={(e) =>
              (e.currentTarget.style.borderColor = "var(--amber)")
            }
            onBlurCapture={(e) =>
              (e.currentTarget.style.borderColor = "var(--border)")
            }
          >
            <span
              style={{
                padding: "0 12px",
                fontFamily: "var(--mono)",
                fontSize: 14,
                color: "var(--text-muted)",
              }}
            >
              ₹
            </span>
            <input
              ref={inputRef}
              type="number"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              onKeyDown={(e) =>
                e.key === "Enter" && onConfirm(parseFloat(target) || null, note)
              }
              placeholder={
                currentPrice
                  ? Math.round(currentPrice * 1.15).toString()
                  : "e.g. 4000"
              }
              style={{
                flex: 1,
                background: "transparent",
                border: "none",
                outline: "none",
                color: "var(--text-primary)",
                fontFamily: "var(--mono)",
                fontSize: 14,
                padding: "11px 12px 11px 0",
              }}
            />
          </div>

          {/* Upside/downside indicator */}
          {upside !== null && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                fontSize: 11,
                fontFamily: "var(--mono)",
                color: isAbove ? "var(--green)" : "var(--red)",
                animation: "fadeUp .2s ease both",
              }}
            >
              {isAbove ? "▲" : "▼"} {Math.abs(upside)}%{" "}
              {isAbove ? "upside" : "downside"} from CMP
            </div>
          )}
        </div>

        {/* Optional note */}
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <label
            style={{
              fontSize: 10,
              letterSpacing: "0.15em",
              textTransform: "uppercase",
              color: "var(--text-muted)",
              fontFamily: "var(--mono)",
            }}
          >
            Note <span style={{ fontWeight: 400 }}>— optional</span>
          </label>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Why are you watching this stock?"
            rows={2}
            style={{
              background: "var(--bg-elevated)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              color: "var(--text-primary)",
              fontFamily: "var(--mono)",
              fontSize: 12,
              padding: "10px 12px",
              outline: "none",
              resize: "none",
              lineHeight: 1.6,
              transition: "border-color .15s",
            }}
            onFocus={(e) => (e.target.style.borderColor = "var(--amber)")}
            onBlur={(e) => (e.target.style.borderColor = "var(--border)")}
          />
        </div>

        {/* Actions */}
        <div style={{ display: "flex", gap: 10 }}>
          <button
            onClick={onCancel}
            style={{
              flex: 1,
              padding: "10px 0",
              background: "transparent",
              border: "1px solid var(--border)",
              borderRadius: 8,
              color: "var(--text-secondary)",
              fontFamily: "var(--mono)",
              fontSize: 12,
              cursor: "pointer",
              letterSpacing: "0.08em",
              transition: "all .15s",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "var(--border-light)";
              e.currentTarget.style.background = "var(--bg-hover)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "var(--border)";
              e.currentTarget.style.background = "transparent";
            }}
          >
            Cancel
          </button>
          <button
            onClick={() => onConfirm(parseFloat(target) || null, note)}
            style={{
              flex: 2,
              padding: "10px 0",
              background: "var(--amber)",
              border: "none",
              borderRadius: 8,
              color: "#fff",
              fontFamily: "var(--mono)",
              fontSize: 12,
              fontWeight: 700,
              cursor: "pointer",
              letterSpacing: "0.1em",
              transition: "opacity .15s",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.opacity = "0.85")}
            onMouseLeave={(e) => (e.currentTarget.style.opacity = "1")}
          >
            ★ Add to Watchlist
          </button>
        </div>
      </div>
    </>
  );
}

// ─── StockHeader ──────────────────────────────────────────────────────────────
export default function StockHeader({ overview, sparkline, onSignInRequired }) {
  const { user } = useAuth();
  const [inWatchlist, setInWatchlist] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showModal, setShowModal] = useState(false);

  // ── Check if already in watchlist ─────────────────────────────────────────
  useEffect(() => {
    if (!user || !overview?.symbol) return;
    supabase
      .from("watchlist")
      .select("id")
      .eq("user_id", user.id)
      .eq("symbol", overview.symbol)
      .maybeSingle()
      .then(({ data }) => {
        setInWatchlist(!!data);
      });
  }, [user, overview?.symbol]);

  // ── Click watchlist button ─────────────────────────────────────────────────
  const handleWatchlistClick = () => {
    if (!user) {
      onSignInRequired?.();
      showToast("Sign in to add stocks to your Watchlist", "error");
      return;
    }
    if (inWatchlist) {
      // Already saved → remove directly (no modal needed)
      handleRemove();
      return;
    }
    // Not saved → open modal to ask target price
    setShowModal(true);
  };

  // ── Confirm from modal → save to Supabase ─────────────────────────────────
  const handleConfirm = async (targetPrice, note) => {
    setShowModal(false);
    setSaving(true);
    const { error } = await supabase.from("watchlist").upsert(
      {
        user_id: user.id,
        symbol: overview.symbol,
        name: overview.name || overview.symbol,
        sector: overview.sector || "",
        price: overview.currentPrice || null,
        target_price: targetPrice || null,
        note: note || null,
      },
      { onConflict: "user_id,symbol" },
    );

    if (!error) {
      setInWatchlist(true);
      showToast(
        `★ ${overview.symbol} added to Watchlist${targetPrice ? ` · Target ₹${targetPrice.toLocaleString("en-IN")}` : ""}`,
      );
    } else {
      showToast("Failed to save — try again", "error");
    }
    setSaving(false);
  };

  // ── Remove from watchlist ─────────────────────────────────────────────────
  const handleRemove = async () => {
    setSaving(true);
    const { error } = await supabase
      .from("watchlist")
      .delete()
      .eq("user_id", user.id)
      .eq("symbol", overview.symbol);
    if (!error) {
      setInWatchlist(false);
      showToast(`Removed ${overview.symbol} from Watchlist`);
    } else {
      showToast("Failed to remove — try again", "error");
    }
    setSaving(false);
  };

  // ── Skeleton ───────────────────────────────────────────────────────────────
  if (!overview)
    return (
      <div className="header-skeleton">
        <div className="skel skel-wide" />
        <div className="skel skel-med" />
        <div className="skel skel-wide" />
      </div>
    );

  const change = (overview.currentPrice || 0) - (overview.previousClose || 0);
  const changePct = overview.previousClose
    ? (change / overview.previousClose) * 100
    : 0;
  const positive = change >= 0;
  const closes = sparkline?.closes || [];

  return (
    <>
      <header className="stock-header">
        <div className="header-top-row">
          {/* Identity */}
          <div className="stock-identity">
            <div className="stock-logo">{overview.symbol?.slice(0, 3)}</div>
            <div>
              <h1 className="stock-name">{overview.name || overview.symbol}</h1>
              <div className="stock-meta-row">
                <span className="mono muted">NSE: {overview.symbol}</span>
                {overview.sector && (
                  <span className="badge badge-sector">{overview.sector}</span>
                )}
              </div>
            </div>
          </div>

          {/* Watchlist button */}
          <button
            className="watchlist-btn"
            onClick={handleWatchlistClick}
            disabled={saving}
            title={
              !user
                ? "Sign in to add to Watchlist"
                : inWatchlist
                  ? "Remove from Watchlist"
                  : "Add to Watchlist"
            }
            style={{
              borderColor: inWatchlist ? "var(--amber)" : undefined,
              color: inWatchlist ? "var(--amber)" : undefined,
              opacity: saving ? 0.6 : 1,
              transition: "all .2s",
            }}
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill={inWatchlist ? "var(--amber)" : "none"}
              stroke="currentColor"
              strokeWidth="2"
              style={{ transition: "fill .2s" }}
            >
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
            </svg>
            {saving
              ? "Saving…"
              : !user
                ? "Sign in to Save"
                : inWatchlist
                  ? "Watching ★"
                  : "Add to Watchlist"}
          </button>
        </div>

        {/* Price Row */}
        <div className="price-row">
          <div className="current-price">
            {fmt.price(overview.currentPrice)}
          </div>
          <div className="change-block">
            <span className={`change-badge ${positive ? "pos" : "neg"}`}>
              {positive ? "▲" : "▼"} {fmt.pct(changePct)}
            </span>
            <span className="change-abs mono">
              {positive ? "+" : ""}
              {fmt.price(change)}
            </span>
          </div>
          <Sparkline closes={closes} positive={positive} />
        </div>

        {/* Metrics Row */}
        <div className="metrics-row">
          <MetricChip
            label="Market Cap"
            value={fmt.crore(overview.marketCap)}
          />
          <MetricChip label="P/E Ratio" value={fmt.ratio(overview.peRatio)} />
          <MetricChip
            label="ROE"
            value={overview.roe ? fmt.num(overview.roe * 100) + "%" : "—"}
          />
          <MetricChip
            label="Div. Yield"
            value={
              overview.dividendYield
                ? fmt.num(overview.dividendYield * 100) + "%"
                : "—"
            }
          />
          <MetricChip label="52W Range">
            <RangeBar
              low={overview.fiftyTwoWeekLow}
              high={overview.fiftyTwoWeekHigh}
              current={overview.currentPrice}
            />
          </MetricChip>
        </div>
      </header>

      {/* Target Price Modal — rendered outside header so it's not clipped */}
      {showModal && (
        <TargetPriceModal
          symbol={overview.symbol}
          currentPrice={overview.currentPrice}
          onConfirm={handleConfirm}
          onCancel={() => setShowModal(false)}
        />
      )}
    </>
  );
}
