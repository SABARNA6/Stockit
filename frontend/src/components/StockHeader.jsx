import { useEffect, useRef } from "react";
import { fmt } from "../api/stockApi";

// ─── Sparkline SVG ────────────────────────────────────────────────────────────
function Sparkline({ closes = [], positive }) {
  if (!closes.length) return null;
  const W = 140, H = 44;
  const min = Math.min(...closes);
  const max = Math.max(...closes);
  const range = max - min || 1;
  const pts = closes.map((v, i) => {
    const x = (i / (closes.length - 1)) * W;
    const y = H - ((v - min) / range) * (H - 6) - 3;
    return `${x},${y}`;
  }).join(" ");
  const color = positive ? "#22c55e" : "#ef4444";
  const fillPts = `0,${H} ${pts} ${W},${H}`;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: W, height: H, display: "block" }} preserveAspectRatio="none">
      <defs>
        <linearGradient id={`sg-${positive}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.25" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon fill={`url(#sg-${positive})`} points={fillPts} />
      <polyline fill="none" stroke={color} strokeWidth="2" points={pts} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// ─── Range Bar ────────────────────────────────────────────────────────────────
function RangeBar({ low, high, current }) {
  if (!low || !high || !current) return null;
  const pct = Math.min(Math.max(((current - low) / (high - low)) * 100, 0), 100);
  return (
    <div style={{ marginTop: 6 }}>
      <div style={{ height: 4, background: "var(--border)", borderRadius: 2, position: "relative" }}>
        <div style={{
          position: "absolute", left: 0, width: "100%", height: "100%",
          background: "linear-gradient(90deg, var(--green), var(--amber), var(--red))",
          borderRadius: 2, opacity: 0.6,
        }} />
        <div style={{
          position: "absolute", left: `${pct}%`, top: "50%",
          transform: "translate(-50%,-50%)",
          width: 10, height: 10, borderRadius: "50%",
          background: "var(--text-primary)",
          boxShadow: "0 0 0 2px var(--bg-card)",
          zIndex: 1,
        }} />
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4 }}>
        <span style={{ fontSize: 9, color: "var(--text-muted)", fontFamily: "var(--mono)" }}>{fmt.price(low)}</span>
        <span style={{ fontSize: 9, color: "var(--text-muted)", fontFamily: "var(--mono)" }}>{fmt.price(high)}</span>
      </div>
    </div>
  );
}

// ─── Metric Chip ─────────────────────────────────────────────────────────────
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

// ─── StockHeader ──────────────────────────────────────────────────────────────
export default function StockHeader({ overview, sparkline, onWatchlist }) {
  if (!overview) return (
    <div className="header-skeleton">
      <div className="skel skel-wide" />
      <div className="skel skel-med" />
      <div className="skel skel-wide" />
    </div>
  );

  const change = (overview.currentPrice || 0) - (overview.previousClose || 0);
  const changePct = overview.previousClose ? (change / overview.previousClose) * 100 : 0;
  const positive = change >= 0;
  const closes = sparkline?.closes || [];

  return (
    <header className="stock-header">
      <div className="header-top-row">
        {/* Identity */}
        <div className="stock-identity">
          <div className="stock-logo">{overview.symbol?.slice(0, 3)}</div>
          <div>
            <h1 className="stock-name">{overview.name || overview.symbol}</h1>
            <div className="stock-meta-row">
              <span className="mono muted">NSE: {overview.symbol}</span>
              {overview.sector && <span className="badge badge-sector">{overview.sector}</span>}
            </div>
          </div>
        </div>

        <button className="watchlist-btn" onClick={onWatchlist}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
          </svg>
          Watchlist
        </button>
      </div>

      {/* Price Row */}
      <div className="price-row">
        <div className="current-price">{fmt.price(overview.currentPrice)}</div>

        <div className="change-block">
          <span className={`change-badge ${positive ? "pos" : "neg"}`}>
            {positive ? "▲" : "▼"} {fmt.pct(changePct)}
          </span>
          <span className="change-abs mono">{positive ? "+" : ""}{fmt.price(change)}</span>
        </div>

        <Sparkline closes={closes} positive={positive} />
      </div>

      {/* Metrics Row */}
      <div className="metrics-row">
        <MetricChip label="Market Cap" value={fmt.crore(overview.marketCap)} />
        <MetricChip label="P/E Ratio" value={fmt.ratio(overview.peRatio)} />
        <MetricChip label="ROE" value={overview.roe ? fmt.num(overview.roe * 100) + "%" : "—"} />
        <MetricChip label="Div. Yield" value={overview.dividendYield ? fmt.num(overview.dividendYield * 100) + "%" : "—"} />
        <MetricChip label="52W Range">
          <RangeBar
            low={overview.fiftyTwoWeekLow}
            high={overview.fiftyTwoWeekHigh}
            current={overview.currentPrice}
          />
        </MetricChip>
      </div>
    </header>
  );
}
