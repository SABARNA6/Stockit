/**
 * PortfolioPage.jsx
 * Full dashboard with sidebar navigation.
 * Sub-pages: Overview · Add Holding · Watchlist · AI Picks · News
 * Backend: Supabase (portfolio + watchlist tables)
 *
 * Required Supabase tables — run in SQL Editor:
 * ─────────────────────────────────────────────
 * create table public.portfolio (
 *   id uuid default gen_random_uuid() primary key,
 *   user_id uuid references auth.users(id) on delete cascade,
 *   symbol text not null,
 *   qty numeric not null,
 *   avg_cost numeric not null,
 *   created_at timestamptz default now()
 * );
 * alter table public.portfolio enable row level security;
 * create policy "own portfolio" on public.portfolio
 *   using (auth.uid() = user_id) with check (auth.uid() = user_id);
 *
 * create table public.watchlist (
 *   id uuid default gen_random_uuid() primary key,
 *   user_id uuid references auth.users(id) on delete cascade,
 *   symbol text not null,
 *   name text,
 *   sector text,
 *   price numeric,
 *   created_at timestamptz default now(),
 *   unique (user_id, symbol)
 * );
 * alter table public.watchlist enable row level security;
 * create policy "own watchlist" on public.watchlist
 *   using (auth.uid() = user_id) with check (auth.uid() = user_id);
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { supabase } from "../supabaseClient";
import { useAuth } from "../context/AuthContext";

// ─── Icons (inline SVG to avoid extra deps) ──────────────────────────────────
const Icon = {
  grid: (
    <svg
      width="16"
      height="16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      viewBox="0 0 24 24"
    >
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" />
      <rect x="14" y="14" width="7" height="7" rx="1" />
    </svg>
  ),
  plus: (
    <svg
      width="16"
      height="16"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      viewBox="0 0 24 24"
    >
      <path d="M12 5v14M5 12h14" />
    </svg>
  ),
  star: (
    <svg
      width="16"
      height="16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      viewBox="0 0 24 24"
    >
      <polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26" />
    </svg>
  ),
  sparkle: (
    <svg
      width="16"
      height="16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      viewBox="0 0 24 24"
    >
      <path d="M12 2l2.4 7.4H22l-6.2 4.5 2.4 7.4L12 17l-6.2 4.3 2.4-7.4L2 9.4h7.6z" />
    </svg>
  ),
  news: (
    <svg
      width="16"
      height="16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      viewBox="0 0 24 24"
    >
      <path d="M4 22h16a2 2 0 002-2V4a2 2 0 00-2-2H8a2 2 0 00-2 2v16a4 4 0 01-4-4V6" />
      <path d="M10 7h6M10 11h6M10 15h4" />
    </svg>
  ),
  trash: (
    <svg
      width="14"
      height="14"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      viewBox="0 0 24 24"
    >
      <polyline points="3,6 5,6 21,6" />
      <path d="M19 6l-1 14H6L5 6" />
      <path d="M10 11v6M14 11v6" />
      <path d="M9 6V4h6v2" />
    </svg>
  ),
  arrow: (
    <svg
      width="14"
      height="14"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      viewBox="0 0 24 24"
    >
      <path d="M5 12h14M12 5l7 7-7 7" />
    </svg>
  ),
  back: (
    <svg
      width="16"
      height="16"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      viewBox="0 0 24 24"
    >
      <path d="M19 12H5M12 5l-7 7 7 7" />
    </svg>
  ),
  chart: (
    <svg
      width="16"
      height="16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      viewBox="0 0 24 24"
    >
      <polyline points="22,12 18,12 15,21 9,3 6,12 2,12" />
    </svg>
  ),
  menu: (
    <svg
      width="18"
      height="18"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      viewBox="0 0 24 24"
    >
      <line x1="3" y1="6" x2="21" y2="6" />
      <line x1="3" y1="12" x2="21" y2="12" />
      <line x1="3" y1="18" x2="21" y2="18" />
    </svg>
  ),
  close: (
    <svg
      width="16"
      height="16"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      viewBox="0 0 24 24"
    >
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  ),
};

// ─── Mock data helpers ────────────────────────────────────────────────────────
const MOCK_PRICES = {
  TCS: 1,
  HCLTECH: 1843,
  SBIN: 842,
  BAJFINANCE: 6890,
  TITAN: 3580,
  INFY: 1842,
  RELIANCE: 2934,
  WIPRO: 478,
  AXISBANK: 1102,
  TATAMOTORS: 996,
  HDFCBANK: 1678,
  ICICIBANK: 1245,
  KOTAKBANK: 1890,
  LTIM: 5430,
  ADANIPORTS: 1340,
};
const mockLTP = (sym, avg) =>
  MOCK_PRICES[sym] || avg * (0.85 + Math.random() * 0.4);

const AI_SUGGESTIONS = [
  {
    symbol: "INFY",
    name: "Infosys Ltd",
    sector: "IT",
    price: 1842,
    score: 92,
    reason: "Strong order book, lower P/E than peers. Pairs well with TCS.",
  },
  {
    symbol: "HDFCBANK",
    name: "HDFC Bank",
    sector: "Banking",
    price: 1678,
    score: 88,
    reason: "Large-cap anchor. Consistent ROE, good for stability.",
  },
  {
    symbol: "RELIANCE",
    name: "Reliance Industries",
    sector: "Conglomerate",
    price: 2934,
    score: 85,
    reason: "Diversifies away from IT. Retail + Jio tailwind.",
  },
  {
    symbol: "LTIM",
    name: "LTIMindtree",
    sector: "IT",
    price: 5430,
    score: 81,
    reason: "High-growth mid-cap IT. Outperforming sector.",
  },
  {
    symbol: "AXISBANK",
    name: "Axis Bank",
    sector: "Banking",
    price: 1102,
    score: 78,
    reason: "Valuation attractive, ROA improving YoY.",
  },
  {
    symbol: "TATAMOTORS",
    name: "Tata Motors",
    sector: "Auto",
    price: 996,
    score: 74,
    reason: "EV pivot, JLR recovery. Diversifies sector exposure.",
  },
];

const PERSONALIZED_NEWS = [
  {
    id: 1,
    symbol: "TCS",
    title: "TCS bags $320M deal with European insurance giant",
    sentiment: "positive",
    source: "Economic Times",
    time: "2h ago",
    summary:
      "TCS wins multi-year digital transformation contract, boosting order book to all-time high.",
  },
  {
    id: 2,
    symbol: "HCLTECH",
    title: "HCL Tech Q4 revenue misses estimates by 1.2%",
    sentiment: "negative",
    source: "Mint",
    time: "4h ago",
    summary:
      "Revenue at ₹28,057 Cr vs expected ₹28,400 Cr. Management guidance remains cautious for H1.",
  },
  {
    id: 3,
    symbol: "SBIN",
    title: "SBI raises FD rates by 25bps across all tenures",
    sentiment: "positive",
    source: "NDTV Profit",
    time: "6h ago",
    summary:
      "Move signals confidence in liquidity. NIM expansion expected Q1 FY26.",
  },
  {
    id: 4,
    symbol: "BAJFINANCE",
    title: "Bajaj Finance NPA rises slightly, asset quality stable",
    sentiment: "neutral",
    source: "Bloomberg",
    time: "8h ago",
    summary:
      "Gross NPA at 1.07% vs 1.02% last quarter. Management calls it transient.",
  },
  {
    id: 5,
    symbol: "TITAN",
    title: "Titan Q4 jewellery revenue up 22% YoY on gold demand",
    sentiment: "positive",
    source: "BSE Filing",
    time: "10h ago",
    summary:
      "Jewellery segment leads; watches segment soft. Expansion into international markets on track.",
  },
  {
    id: 6,
    symbol: "TCS",
    title: "TCS announces ₹17,000 Cr buyback at ₹4,150 per share",
    sentiment: "positive",
    source: "CNBC TV18",
    time: "1d ago",
    summary:
      "5th consecutive buyback signals strong cash generation. Expected to boost EPS.",
  },
];

// ─── Allocation Pie ───────────────────────────────────────────────────────────
const PIE_COLORS = [
  "#3b82f6",
  "#10d68e",
  "#8b5cf6",
  "#f0a030",
  "#f04060",
  "#06b6d4",
  "#f472b6",
  "#a3e635",
];
function AllocationPie({ holdings }) {
  const total = holdings.reduce((s, h) => s + h.currentValue, 0);
  if (!total) return null;
  let cum = -Math.PI / 2;
  const cx = 90,
    cy = 90,
    r = 70,
    ir = 42;
  const slices = holdings.map((h, i) => {
    const pct = h.currentValue / total;
    const s = cum;
    cum += pct * 2 * Math.PI;
    const e = cum;
    const large = pct > 0.5 ? 1 : 0;
    const p = (a, rad) => [cx + rad * Math.cos(a), cy + rad * Math.sin(a)];
    const [x1, y1] = p(s, r),
      [x2, y2] = p(e, r),
      [ix1, iy1] = p(s, ir),
      [ix2, iy2] = p(e, ir);
    return {
      d: `M${x1},${y1}A${r},${r},0,${large},1,${x2},${y2}L${ix2},${iy2}A${ir},${ir},0,${large},0,${ix1},${iy1}Z`,
      pct,
      color: PIE_COLORS[i % PIE_COLORS.length],
      symbol: h.symbol,
    };
  });
  return (
    <div
      style={{
        display: "flex",
        gap: 20,
        alignItems: "center",
        flexWrap: "wrap",
      }}
    >
      <svg width={180} height={180} style={{ flexShrink: 0 }}>
        {slices.map((s, i) => (
          <path
            key={i}
            d={s.d}
            fill={s.color}
            opacity={0.9}
            stroke="var(--bg-card)"
            strokeWidth={2}
          >
            <title>
              {s.symbol}: {(s.pct * 100).toFixed(1)}%
            </title>
          </path>
        ))}
        <text
          x={cx}
          y={cy - 6}
          textAnchor="middle"
          fill="var(--text-primary)"
          fontSize={13}
          fontFamily="var(--mono)"
          fontWeight={700}
        >
          ₹{(total / 100000).toFixed(1)}L
        </text>
        <text
          x={cx}
          y={cx + 10}
          textAnchor="middle"
          fill="var(--text-muted)"
          fontSize={8}
          fontFamily="var(--mono)"
          letterSpacing={1}
        >
          TOTAL
        </text>
      </svg>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 6,
          flex: 1,
          minWidth: 130,
        }}
      >
        {holdings.map((h, i) => (
          <div
            key={h.symbol}
            style={{ display: "flex", alignItems: "center", gap: 7 }}
          >
            <div
              style={{
                width: 9,
                height: 9,
                borderRadius: 2,
                background: PIE_COLORS[i % PIE_COLORS.length],
                flexShrink: 0,
              }}
            />
            <span
              style={{
                fontSize: 11,
                color: "var(--text-secondary)",
                flex: 1,
                fontFamily: "var(--mono)",
              }}
            >
              {h.symbol}
            </span>
            <span
              style={{
                fontSize: 10,
                color: "var(--text-muted)",
                fontFamily: "var(--mono)",
              }}
            >
              {((h.currentValue / total) * 100).toFixed(1)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Health Ring ──────────────────────────────────────────────────────────────
function HealthRing({ score }) {
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

// ─── Stat Card ────────────────────────────────────────────────────────────────
function StatCard({ label, value, sub, color, delay = "0s" }) {
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

// ─── Section header ───────────────────────────────────────────────────────────
function PageHeader({ icon, title, sub, action }) {
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

// ═══════════════════════════════════════════════════════════════════════════════
// SUB-PAGE: OVERVIEW
// ═══════════════════════════════════════════════════════════════════════════════
function OverviewPage({ holdings, watchlistCount, onNavigate }) {
  const totalInvested = holdings.reduce((s, h) => s + h.qty * h.avg_cost, 0);
  const totalCurrent = holdings.reduce((s, h) => s + h.currentValue, 0);
  const totalPnL = totalCurrent - totalInvested;
  const totalRet =
    totalInvested > 0 ? ((totalPnL / totalInvested) * 100).toFixed(2) : 0;
  const health = Math.min(
    100,
    Math.round(
      (holdings.length >= 5 ? 30 : holdings.length * 6) +
        (totalRet > 0
          ? Math.min(40, totalRet * 2)
          : Math.max(0, 40 + parseFloat(totalRet) * 2)) +
        (holdings.length >= 3 ? 30 : holdings.length * 10),
    ),
  );

  const topGainer = [...holdings].sort(
    (a, b) =>
      b.currentValue -
      b.qty * b.avg_cost -
      (a.currentValue - a.qty * a.avg_cost),
  )[0];
  const topLoser = [...holdings].sort(
    (a, b) =>
      a.currentValue -
      a.qty * a.avg_cost -
      (b.currentValue - b.qty * b.avg_cost),
  )[0];

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 24,
        animation: "fadeUp .35s ease both",
      }}
    >
      <PageHeader
        icon={Icon.grid}
        title="Portfolio Overview"
        sub={`${holdings.length} holdings · Last refreshed just now`}
      />

      {/* Stats row */}
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        <StatCard
          label="Invested"
          value={`₹${(totalInvested / 1000).toFixed(1)}K`}
          sub={`${holdings.length} stocks`}
          delay="0s"
        />
        <StatCard
          label="Current Value"
          value={`₹${(totalCurrent / 1000).toFixed(1)}K`}
          color={totalPnL >= 0 ? "var(--green)" : "var(--red)"}
          delay=".05s"
        />
        <StatCard
          label="Total P&L"
          value={`${totalPnL >= 0 ? "+" : ""}₹${(totalPnL / 1000).toFixed(1)}K`}
          sub={`${totalPnL >= 0 ? "▲" : "▼"} ${Math.abs(totalRet)}%`}
          color={totalPnL >= 0 ? "var(--green)" : "var(--red)"}
          delay=".1s"
        />
        <StatCard
          label="Watchlist"
          value={watchlistCount}
          sub="stocks tracked"
          color="var(--amber)"
          delay=".15s"
        />
      </div>

      {/* Charts row */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 180px",
          gap: 16,
          alignItems: "start",
        }}
      >
        {/* Allocation */}
        <div
          style={{
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            borderRadius: 12,
            padding: 20,
          }}
        >
          <div
            style={{
              fontSize: 9,
              letterSpacing: "0.18em",
              color: "var(--text-muted)",
              fontFamily: "var(--mono)",
              textTransform: "uppercase",
              marginBottom: 14,
            }}
          >
            Allocation
          </div>
          {holdings.length > 0 ? (
            <AllocationPie holdings={holdings} />
          ) : (
            <div
              style={{
                textAlign: "center",
                color: "var(--text-muted)",
                fontSize: 12,
                padding: "32px 0",
              }}
            >
              No holdings yet
            </div>
          )}
        </div>
        {/* Health */}
        <div
          style={{
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            borderRadius: 12,
            padding: 20,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 8,
          }}
        >
          <div
            style={{
              fontSize: 9,
              letterSpacing: "0.18em",
              color: "var(--text-muted)",
              fontFamily: "var(--mono)",
              textTransform: "uppercase",
            }}
          >
            Portfolio Health
          </div>
          <HealthRing score={health} />
          <p
            style={{
              fontSize: 10,
              color: "var(--text-muted)",
              fontFamily: "var(--mono)",
              textAlign: "center",
              lineHeight: 1.6,
            }}
          >
            {health >= 75
              ? "Well diversified"
              : health >= 50
                ? "Add more variety"
                : "High concentration risk"}
          </p>
        </div>
      </div>

      {/* Top mover cards */}
      {holdings.length > 0 && (
        <div
          style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}
        >
          {[
            {
              label: "Top Gainer",
              holding: topGainer,
              color: "var(--green)",
              bg: "var(--green-bg)",
            },
            {
              label: "Top Loser",
              holding: topLoser,
              color: "var(--red)",
              bg: "var(--red-bg)",
            },
          ].map(({ label, holding, color, bg }) => {
            if (!holding) return null;
            const pnl = holding.currentValue - holding.qty * holding.avg_cost;
            const ret = (
              (pnl / (holding.qty * holding.avg_cost)) *
              100
            ).toFixed(2);
            return (
              <div
                key={label}
                style={{
                  background: "var(--bg-card)",
                  border: `1px solid var(--border)`,
                  borderRadius: 12,
                  padding: 18,
                }}
              >
                <div
                  style={{
                    fontSize: 9,
                    letterSpacing: "0.18em",
                    color: "var(--text-muted)",
                    fontFamily: "var(--mono)",
                    textTransform: "uppercase",
                    marginBottom: 10,
                  }}
                >
                  {label}
                </div>
                <div
                  style={{
                    fontSize: 16,
                    fontWeight: 700,
                    color: "var(--text-primary)",
                    fontFamily: "var(--mono)",
                  }}
                >
                  {holding.symbol}
                </div>
                <div
                  style={{
                    fontSize: 13,
                    color,
                    fontFamily: "var(--mono)",
                    marginTop: 4,
                  }}
                >
                  {pnl >= 0 ? "+" : ""}₹{(pnl / 1000).toFixed(1)}K ({ret}%)
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Quick actions */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3,1fr)",
          gap: 10,
        }}
      >
        {[
          {
            label: "Add Holding",
            sub: "Track a new stock",
            icon: Icon.plus,
            page: "add",
            color: "var(--green)",
          },
          {
            label: "View Watchlist",
            sub: "Stocks you're watching",
            icon: Icon.star,
            page: "watchlist",
            color: "var(--amber)",
          },
          {
            label: "AI Picks",
            sub: "Personalised for you",
            icon: Icon.sparkle,
            page: "ai",
            color: "var(--purple)",
          },
        ].map((a) => (
          <button
            key={a.page}
            onClick={() => onNavigate(a.page)}
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 6,
              padding: "16px 18px",
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              borderRadius: 12,
              cursor: "pointer",
              textAlign: "left",
              transition: "all .15s",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = a.color;
              e.currentTarget.style.background = "var(--bg-hover)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "var(--border)";
              e.currentTarget.style.background = "var(--bg-card)";
            }}
          >
            <span style={{ color: a.color }}>{a.icon}</span>
            <span
              style={{
                fontSize: 12,
                fontWeight: 600,
                color: "var(--text-primary)",
              }}
            >
              {a.label}
            </span>
            <span
              style={{
                fontSize: 10,
                color: "var(--text-muted)",
                fontFamily: "var(--mono)",
              }}
            >
              {a.sub}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// SUB-PAGE: HOLDINGS
// ═══════════════════════════════════════════════════════════════════════════════
function getAISignal(sym, avg, ltp) {
  const chg = ((ltp - avg) / avg) * 100;
  if (chg > 15)
    return {
      v: "BOOK",
      c: "var(--amber)",
      bg: "var(--amber-bg)",
      r: "Strong gain — consider partial booking",
    };
  if (chg < -12)
    return {
      v: "HOLD",
      c: "var(--blue)",
      bg: "var(--blue-bg)",
      r: "Temporary dip, fundamentals intact",
    };
  if (chg > 5)
    return {
      v: "HOLD",
      c: "var(--green)",
      bg: "var(--green-bg)",
      r: "On track — let it ride",
    };
  return {
    v: "BUY",
    c: "var(--green)",
    bg: "var(--green-bg)",
    r: "Good entry for averaging down",
  };
}

function HoldingsPage({ holdings, onDelete, onNavigateAdd }) {
  const totalInvested = holdings.reduce((s, h) => s + h.qty * h.avg_cost, 0);
  const totalCurrent = holdings.reduce((s, h) => s + h.currentValue, 0);
  const totalPnL = totalCurrent - totalInvested;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 20,
        animation: "fadeUp .35s ease both",
      }}
    >
      <PageHeader
        icon={Icon.chart}
        title="My Holdings"
        sub={`${holdings.length} stocks · P&L ${totalPnL >= 0 ? "+" : ""}₹${(totalPnL / 1000).toFixed(1)}K`}
        action={
          <button
            onClick={onNavigateAdd}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "8px 16px",
              background: "var(--green)",
              border: "none",
              borderRadius: 8,
              color: "#fff",
              fontFamily: "var(--mono)",
              fontSize: 11,
              cursor: "pointer",
              letterSpacing: "0.1em",
            }}
          >
            {Icon.plus} Add Holding
          </button>
        }
      />

      {holdings.length === 0 ? (
        <div
          style={{
            textAlign: "center",
            padding: "60px 20px",
            border: "1px dashed var(--border)",
            borderRadius: 12,
            color: "var(--text-muted)",
            fontSize: 13,
          }}
        >
          <div style={{ fontSize: 32, marginBottom: 12 }}>📊</div>
          No holdings yet.{" "}
          <span
            style={{ color: "var(--green)", cursor: "pointer" }}
            onClick={onNavigateAdd}
          >
            Add your first stock →
          </span>
        </div>
      ) : (
        <>
          {/* Mobile cards / Desktop table */}
          <div
            style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              borderRadius: 12,
              overflow: "hidden",
            }}
          >
            <div style={{ overflowX: "auto" }}>
              <table
                style={{
                  width: "100%",
                  borderCollapse: "collapse",
                  minWidth: 700,
                }}
              >
                <thead>
                  <tr style={{ background: "var(--bg-elevated)" }}>
                    {[
                      "Symbol",
                      "Qty",
                      "Avg Cost",
                      "LTP",
                      "Invested",
                      "Current",
                      "P&L",
                      "Return",
                      "Signal",
                      "",
                    ].map((h) => (
                      <th
                        key={h}
                        style={{
                          padding: "10px 14px",
                          textAlign: "left",
                          fontFamily: "var(--mono)",
                          fontSize: 9,
                          fontWeight: 600,
                          letterSpacing: "0.15em",
                          textTransform: "uppercase",
                          color: "var(--text-muted)",
                          whiteSpace: "nowrap",
                          borderBottom: "1px solid var(--border)",
                        }}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {holdings.map((h) => {
                    const invested = h.qty * h.avg_cost;
                    const pnl = h.currentValue - invested;
                    const ret = ((pnl / invested) * 100).toFixed(2);
                    const sig = getAISignal(h.symbol, h.avg_cost, h.ltp);
                    const pos = pnl >= 0;
                    return (
                      <tr
                        key={h.id}
                        style={{
                          borderBottom: "1px solid var(--border)",
                          transition: "background .12s",
                        }}
                        onMouseEnter={(e) =>
                          (e.currentTarget.style.background = "var(--bg-hover)")
                        }
                        onMouseLeave={(e) =>
                          (e.currentTarget.style.background = "transparent")
                        }
                      >
                        <td style={{ padding: "12px 14px" }}>
                          <span
                            style={{
                              fontFamily: "var(--mono)",
                              fontSize: 13,
                              fontWeight: 700,
                              color: "var(--blue)",
                            }}
                          >
                            {h.symbol}
                          </span>
                        </td>
                        <td
                          style={{
                            padding: "12px 14px",
                            fontFamily: "var(--mono)",
                            fontSize: 12,
                            color: "var(--text-secondary)",
                          }}
                        >
                          {h.qty}
                        </td>
                        <td
                          style={{
                            padding: "12px 14px",
                            fontFamily: "var(--mono)",
                            fontSize: 12,
                            color: "var(--text-secondary)",
                          }}
                        >
                          ₹{h.avg_cost.toLocaleString("en-IN")}
                        </td>
                        <td
                          style={{
                            padding: "12px 14px",
                            fontFamily: "var(--mono)",
                            fontSize: 12,
                            color: pos ? "var(--green)" : "var(--red)",
                          }}
                        >
                          ₹
                          {h.ltp.toLocaleString("en-IN", {
                            maximumFractionDigits: 0,
                          })}
                        </td>
                        <td
                          style={{
                            padding: "12px 14px",
                            fontFamily: "var(--mono)",
                            fontSize: 12,
                            color: "var(--text-secondary)",
                          }}
                        >
                          ₹{(invested / 1000).toFixed(1)}K
                        </td>
                        <td
                          style={{
                            padding: "12px 14px",
                            fontFamily: "var(--mono)",
                            fontSize: 12,
                            color: "var(--text-secondary)",
                          }}
                        >
                          ₹{(h.currentValue / 1000).toFixed(1)}K
                        </td>
                        <td
                          style={{
                            padding: "12px 14px",
                            fontFamily: "var(--mono)",
                            fontSize: 12,
                            color: pos ? "var(--green)" : "var(--red)",
                          }}
                        >
                          {pos ? "+" : ""}₹{(pnl / 1000).toFixed(1)}K
                        </td>
                        <td
                          style={{
                            padding: "12px 14px",
                            fontFamily: "var(--mono)",
                            fontSize: 12,
                            color: pos ? "var(--green)" : "var(--red)",
                          }}
                        >
                          {pos ? "▲" : "▼"}
                          {Math.abs(ret)}%
                        </td>
                        <td style={{ padding: "12px 14px" }}>
                          <span
                            title={sig.r}
                            style={{
                              padding: "3px 9px",
                              borderRadius: 20,
                              fontSize: 9,
                              fontFamily: "var(--mono)",
                              fontWeight: 700,
                              letterSpacing: "0.1em",
                              background: sig.bg,
                              color: sig.c,
                              border: `1px solid ${sig.c}`,
                            }}
                          >
                            {sig.v}
                          </span>
                        </td>
                        <td style={{ padding: "12px 14px" }}>
                          <button
                            onClick={() => onDelete(h.id)}
                            style={{
                              background: "transparent",
                              border: "none",
                              color: "var(--text-muted)",
                              cursor: "pointer",
                              display: "flex",
                              alignItems: "center",
                            }}
                            title="Remove holding"
                            onMouseEnter={(e) =>
                              (e.currentTarget.style.color = "var(--red)")
                            }
                            onMouseLeave={(e) =>
                              (e.currentTarget.style.color =
                                "var(--text-muted)")
                            }
                          >
                            {Icon.trash}
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
          {/* Signal legend */}
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
            {[
              {
                v: "BUY",
                c: "var(--green)",
                bg: "var(--green-bg)",
                d: "Good entry / average down",
              },
              {
                v: "HOLD",
                c: "var(--blue)",
                bg: "var(--blue-bg)",
                d: "Fundamentals intact",
              },
              {
                v: "BOOK",
                c: "var(--amber)",
                bg: "var(--amber-bg)",
                d: "Partial profit booking",
              },
            ].map((s) => (
              <div
                key={s.v}
                style={{ display: "flex", alignItems: "center", gap: 6 }}
              >
                <span
                  style={{
                    padding: "2px 8px",
                    borderRadius: 20,
                    fontSize: 9,
                    fontFamily: "var(--mono)",
                    fontWeight: 700,
                    background: s.bg,
                    color: s.c,
                    border: `1px solid ${s.c}`,
                  }}
                >
                  {s.v}
                </span>
                <span style={{ fontSize: 10, color: "var(--text-muted)" }}>
                  {s.d}
                </span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// SUB-PAGE: ADD HOLDING
// ═══════════════════════════════════════════════════════════════════════════════
function AddHoldingPage({ userId, onSaved }) {
  const [tab, setTab] = useState("manual");
  const [rows, setRows] = useState([{ symbol: "", qty: "", avg_cost: "" }]);
  const [csv, setCsv] = useState("");
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState({ type: "", text: "" });
  const fileRef = useRef();

  const addRow = () =>
    setRows((r) => [...r, { symbol: "", qty: "", avg_cost: "" }]);
  const removeRow = (i) => setRows((r) => r.filter((_, j) => j !== i));
  const update = (i, f, v) =>
    setRows((r) => r.map((row, j) => (j === i ? { ...row, [f]: v } : row)));

  const parseCSV = (text) => {
    const lines = text.trim().split("\n").filter(Boolean);
    return lines
      .slice(1)
      .map((l) => {
        const [symbol, qty, avg_cost] = l.split(",").map((s) => s.trim());
        return {
          symbol: symbol?.toUpperCase(),
          qty: parseFloat(qty),
          avg_cost: parseFloat(avg_cost),
        };
      })
      .filter((r) => r.symbol && !isNaN(r.qty) && !isNaN(r.avg_cost));
  };

  const handleSave = async () => {
    setMsg({ type: "", text: "" });
    setSaving(true);
    try {
      let data =
        tab === "manual"
          ? rows
              .filter((r) => r.symbol && r.qty && r.avg_cost)
              .map((r) => ({
                user_id: userId,
                symbol: r.symbol.toUpperCase(),
                qty: parseFloat(r.qty),
                avg_cost: parseFloat(r.avg_cost),
              }))
          : parseCSV(csv).map((r) => ({ ...r, user_id: userId }));

      if (!data.length)
        throw new Error("Nothing to save. Fill at least one row.");

      const { error } = await supabase.from("portfolio").insert(data);
      if (error) throw error;

      setMsg({
        type: "success",
        text: `✓ ${data.length} holding${data.length > 1 ? "s" : ""} saved successfully.`,
      });
      setRows([{ symbol: "", qty: "", avg_cost: "" }]);
      setCsv("");
      onSaved(); // refresh parent
    } catch (err) {
      setMsg({ type: "error", text: `⚠ ${err.message}` });
    }
    setSaving(false);
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 20,
        animation: "fadeUp .35s ease both",
        maxWidth: 620,
      }}
    >
      <PageHeader
        icon={Icon.plus}
        title="Add Holdings"
        sub="Track your investments — stored securely in your account"
      />

      {/* Tabs */}
      <div
        style={{
          display: "flex",
          background: "var(--bg-elevated)",
          borderRadius: 8,
          padding: 3,
          width: "fit-content",
          border: "1px solid var(--border)",
        }}
      >
        {[
          ["manual", "Manual Entry"],
          ["csv", "CSV / Paste"],
        ].map(([id, label]) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            style={{
              padding: "7px 18px",
              background: tab === id ? "var(--bg-card)" : "transparent",
              border: "none",
              borderRadius: 6,
              color: tab === id ? "var(--text-primary)" : "var(--text-muted)",
              fontFamily: "var(--mono)",
              fontSize: 11,
              cursor: "pointer",
              letterSpacing: "0.08em",
              transition: "all .15s",
            }}
          >
            {label}
          </button>
        ))}
      </div>

      <div
        style={{
          background: "var(--bg-card)",
          border: "1px solid var(--border)",
          borderRadius: 12,
          padding: 24,
          display: "flex",
          flexDirection: "column",
          gap: 16,
        }}
      >
        {msg.text && (
          <div
            style={{
              padding: "10px 14px",
              background:
                msg.type === "success" ? "var(--green-bg)" : "var(--red-bg)",
              border: `1px solid ${msg.type === "success" ? "var(--green)" : "var(--red)"}`,
              borderRadius: 8,
              fontSize: 12,
              color: msg.type === "success" ? "var(--green)" : "var(--red)",
              fontFamily: "var(--mono)",
            }}
          >
            {msg.text}
          </div>
        )}

        {tab === "manual" && (
          <>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 90px 130px 36px",
                gap: 8,
              }}
            >
              {["SYMBOL", "QTY", "AVG COST (₹)", ""].map((h, i) => (
                <span
                  key={i}
                  style={{
                    fontSize: 9,
                    letterSpacing: "0.15em",
                    color: "var(--text-muted)",
                    fontFamily: "var(--mono)",
                    paddingLeft: 4,
                  }}
                >
                  {h}
                </span>
              ))}
            </div>
            {rows.map((row, i) => (
              <div
                key={i}
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 90px 130px 36px",
                  gap: 8,
                }}
              >
                {[
                  ["symbol", "e.g. TCS"],
                  ["qty", "50"],
                  ["avg_cost", "3450"],
                ].map(([f, ph]) => (
                  <input
                    key={f}
                    value={row[f]}
                    onChange={(e) => update(i, f, e.target.value)}
                    placeholder={ph}
                    style={{
                      background: "var(--bg-elevated)",
                      border: "1px solid var(--border)",
                      borderRadius: 6,
                      color: "var(--text-primary)",
                      fontFamily: "var(--mono)",
                      fontSize: 12,
                      padding: "9px 11px",
                      outline: "none",
                      width: "100%",
                      transition: "border-color .15s",
                    }}
                    onFocus={(e) =>
                      (e.target.style.borderColor = "var(--green)")
                    }
                    onBlur={(e) =>
                      (e.target.style.borderColor = "var(--border)")
                    }
                  />
                ))}
                <button
                  onClick={() => removeRow(i)}
                  disabled={rows.length === 1}
                  style={{
                    background: "var(--red-bg)",
                    border: "1px solid var(--red)",
                    borderRadius: 6,
                    color: "var(--red)",
                    cursor: rows.length === 1 ? "not-allowed" : "pointer",
                    fontSize: 16,
                    fontWeight: 700,
                    opacity: rows.length === 1 ? 0.4 : 1,
                  }}
                >
                  ×
                </button>
              </div>
            ))}
            <button
              onClick={addRow}
              style={{
                padding: "9px 0",
                background: "transparent",
                border: "1px dashed var(--border-light)",
                borderRadius: 6,
                color: "var(--text-muted)",
                fontFamily: "var(--mono)",
                fontSize: 11,
                cursor: "pointer",
                letterSpacing: "0.08em",
                transition: "all .15s",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = "var(--green)";
                e.currentTarget.style.color = "var(--green)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "var(--border-light)";
                e.currentTarget.style.color = "var(--text-muted)";
              }}
            >
              + Add Row
            </button>
          </>
        )}

        {tab === "csv" && (
          <>
            <div
              style={{
                background: "var(--bg-elevated)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                padding: 12,
                fontSize: 11,
                fontFamily: "var(--mono)",
                color: "var(--text-muted)",
                lineHeight: 2,
              }}
            >
              <div style={{ color: "var(--green)", marginBottom: 2 }}>
                Expected format (header required):
              </div>
              <div>Symbol,Qty,Avg Cost</div>
              <div>TCS,50,3450</div>
              <div>HCLTECH,30,1620</div>
            </div>
            <button
              onClick={() => fileRef.current?.click()}
              style={{
                padding: "9px 0",
                background: "var(--blue-bg)",
                border: "1px solid var(--blue)",
                borderRadius: 8,
                color: "var(--blue)",
                fontFamily: "var(--mono)",
                fontSize: 11,
                cursor: "pointer",
                letterSpacing: "0.08em",
              }}
            >
              📎 Upload CSV / Excel file
            </button>
            <input
              ref={fileRef}
              type="file"
              accept=".csv,.txt"
              style={{ display: "none" }}
              onChange={(e) => {
                const r = new FileReader();
                r.onload = (ev) => setCsv(ev.target.result);
                r.readAsText(e.target.files[0]);
              }}
            />
            <span
              style={{
                fontSize: 10,
                color: "var(--text-muted)",
                textAlign: "center",
                fontFamily: "var(--mono)",
              }}
            >
              — or paste below —
            </span>
            <textarea
              value={csv}
              onChange={(e) => setCsv(e.target.value)}
              rows={6}
              placeholder={"Symbol,Qty,Avg Cost\nTCS,50,3450"}
              style={{
                background: "var(--bg-elevated)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                color: "var(--text-primary)",
                fontFamily: "var(--mono)",
                fontSize: 12,
                padding: 12,
                resize: "vertical",
                outline: "none",
                lineHeight: 1.8,
              }}
            />
          </>
        )}

        <button
          onClick={handleSave}
          disabled={saving}
          style={{
            padding: "13px 0",
            background: "var(--green)",
            border: "none",
            borderRadius: 8,
            color: "#fff",
            fontFamily: "var(--mono)",
            fontSize: 13,
            fontWeight: 700,
            cursor: saving ? "not-allowed" : "pointer",
            letterSpacing: "0.1em",
            opacity: saving ? 0.7 : 1,
            transition: "opacity .2s",
          }}
        >
          {saving ? "Saving..." : "▲ Save to Portfolio"}
        </button>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// SUB-PAGE: WISHLIST
// ═══════════════════════════════════════════════════════════════════════════════
function WatchlistPage({ items, onDelete, onAdd }) {
  const [symbol, setSymbol] = useState("");
  const [name, setName] = useState("");
  const [sector, setSector] = useState("");
  const [price, setPrice] = useState("");
  const [adding, setAdding] = useState(false);
  const [showForm, setShowForm] = useState(false);

  const handleAdd = async () => {
    if (!symbol) return;
    setAdding(true);
    await onAdd({
      symbol: symbol.toUpperCase(),
      name,
      sector,
      price: parseFloat(price) || null,
    });
    setSymbol("");
    setName("");
    setSector("");
    setPrice("");
    setShowForm(false);
    setAdding(false);
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 20,
        animation: "fadeUp .35s ease both",
      }}
    >
      <PageHeader
        icon={Icon.star}
        title="Watchlist"
        sub={`${items.length} stocks on your radar`}
        action={
          <button
            onClick={() => setShowForm((f) => !f)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "8px 16px",
              background: showForm ? "var(--bg-elevated)" : "var(--amber-bg)",
              border: `1px solid ${showForm ? "var(--border)" : "var(--amber)"}`,
              borderRadius: 8,
              color: showForm ? "var(--text-muted)" : "var(--amber)",
              fontFamily: "var(--mono)",
              fontSize: 11,
              cursor: "pointer",
              letterSpacing: "0.1em",
            }}
          >
            {showForm ? Icon.close : Icon.plus}{" "}
            {showForm ? "Cancel" : "Add Stock"}
          </button>
        }
      />

      {/* Quick-add form */}
      {showForm && (
        <div
          style={{
            background: "var(--bg-card)",
            border: "1px solid var(--amber)",
            borderRadius: 12,
            padding: 20,
            display: "flex",
            flexDirection: "column",
            gap: 12,
            animation: "fadeUp .2s ease both",
          }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr 1fr 1fr",
              gap: 10,
            }}
          >
            {[
              ["Symbol", "symbol", symbol, setSymbol, "INFY"],
              ["Company Name", "name", name, setName, "Infosys Ltd"],
              ["Sector", "sector", sector, setSector, "IT"],
              ["Target Price ₹", "price", price, setPrice, "1900"],
            ].map(([label, _, val, set, ph]) => (
              <div
                key={label}
                style={{ display: "flex", flexDirection: "column", gap: 5 }}
              >
                <span
                  style={{
                    fontSize: 9,
                    letterSpacing: "0.15em",
                    color: "var(--text-muted)",
                    fontFamily: "var(--mono)",
                    textTransform: "uppercase",
                  }}
                >
                  {label}
                </span>
                <input
                  value={val}
                  onChange={(e) => set(e.target.value)}
                  placeholder={ph}
                  style={{
                    background: "var(--bg-elevated)",
                    border: "1px solid var(--border)",
                    borderRadius: 6,
                    color: "var(--text-primary)",
                    fontFamily: "var(--mono)",
                    fontSize: 12,
                    padding: "9px 11px",
                    outline: "none",
                    transition: "border-color .15s",
                  }}
                  onFocus={(e) => (e.target.style.borderColor = "var(--amber)")}
                  onBlur={(e) => (e.target.style.borderColor = "var(--border)")}
                />
              </div>
            ))}
          </div>
          <button
            onClick={handleAdd}
            disabled={adding || !symbol}
            style={{
              padding: "10px 0",
              background: "var(--amber)",
              border: "none",
              borderRadius: 8,
              color: "#fff",
              fontFamily: "var(--mono)",
              fontSize: 12,
              fontWeight: 700,
              cursor: adding || !symbol ? "not-allowed" : "pointer",
              letterSpacing: "0.1em",
              opacity: !symbol ? 0.5 : 1,
            }}
          >
            {adding ? "Adding..." : "★ Add to Watchlist"}
          </button>
        </div>
      )}

      {items.length === 0 ? (
        <div
          style={{
            textAlign: "center",
            padding: "60px 20px",
            border: "1px dashed var(--border)",
            borderRadius: 12,
            color: "var(--text-muted)",
            fontSize: 13,
          }}
        >
          <div style={{ fontSize: 32, marginBottom: 12 }}>⭐</div>
          Your watchlist is empty. Add stocks you want to track.
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill,minmax(260px,1fr))",
            gap: 14,
          }}
        >
          {items.map((item) => {
            const ltp = mockLTP(item.symbol, item.price || 1000);
            const diff = item.price
              ? (((ltp - item.price) / item.price) * 100).toFixed(1)
              : null;
            return (
              <div
                key={item.id}
                style={{
                  background: "var(--bg-card)",
                  border: "1px solid var(--border)",
                  borderRadius: 12,
                  padding: 18,
                  display: "flex",
                  flexDirection: "column",
                  gap: 10,
                  transition: "border-color .15s, transform .15s",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = "var(--amber)";
                  e.currentTarget.style.transform = "translateY(-2px)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "var(--border)";
                  e.currentTarget.style.transform = "none";
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                  }}
                >
                  <div>
                    <div
                      style={{
                        fontFamily: "var(--mono)",
                        fontSize: 14,
                        fontWeight: 700,
                        color: "var(--text-primary)",
                      }}
                    >
                      {item.symbol}
                    </div>
                    {item.name && (
                      <div
                        style={{
                          fontSize: 11,
                          color: "var(--text-secondary)",
                          marginTop: 2,
                        }}
                      >
                        {item.name}
                      </div>
                    )}
                  </div>
                  <button
                    onClick={() => onDelete(item.id)}
                    style={{
                      background: "transparent",
                      border: "none",
                      color: "var(--text-muted)",
                      cursor: "pointer",
                      padding: 2,
                    }}
                    onMouseEnter={(e) =>
                      (e.currentTarget.style.color = "var(--red)")
                    }
                    onMouseLeave={(e) =>
                      (e.currentTarget.style.color = "var(--text-muted)")
                    }
                  >
                    {Icon.trash}
                  </button>
                </div>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <span
                    style={{
                      fontFamily: "var(--mono)",
                      fontSize: 14,
                      fontWeight: 600,
                      color: "var(--text-primary)",
                    }}
                  >
                    ₹{ltp.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
                  </span>
                  {item.sector && (
                    <span
                      style={{
                        fontSize: 9,
                        padding: "2px 8px",
                        borderRadius: 20,
                        background: "var(--blue-bg)",
                        color: "var(--blue)",
                        fontFamily: "var(--mono)",
                        letterSpacing: "0.08em",
                      }}
                    >
                      {item.sector}
                    </span>
                  )}
                </div>
                {item.price && (
                  <div
                    style={{
                      fontSize: 11,
                      fontFamily: "var(--mono)",
                      color: diff >= 0 ? "var(--green)" : "var(--red)",
                    }}
                  >
                    Target ₹{item.price.toLocaleString("en-IN")} ·{" "}
                    {diff >= 0 ? "▲" : "▼"}
                    {Math.abs(diff)}% from target
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// SUB-PAGE: AI RECOMMENDATIONS
// ═══════════════════════════════════════════════════════════════════════════════
function AIPicksPage({ holdings, watchlist, onAddWatchlist }) {
  const [budget, setBudget] = useState(50000);
  const holdingSymbols = new Set(holdings.map((h) => h.symbol));
  const watchlistSymbols = new Set(watchlist.map((w) => w.symbol));

  const suggestions = AI_SUGGESTIONS.filter(
    (s) => !holdingSymbols.has(s.symbol),
  );

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 20,
        animation: "fadeUp .35s ease both",
      }}
    >
      <PageHeader
        icon={Icon.sparkle}
        title="AI Investment Picks"
        sub="Personalised suggestions based on your portfolio composition"
        action={
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span
              style={{
                fontSize: 11,
                color: "var(--text-muted)",
                fontFamily: "var(--mono)",
              }}
            >
              Budget:
            </span>
            <input
              type="number"
              value={budget}
              onChange={(e) => setBudget(Number(e.target.value))}
              style={{
                background: "var(--bg-elevated)",
                border: "1px solid var(--border)",
                borderRadius: 6,
                color: "var(--text-primary)",
                fontFamily: "var(--mono)",
                fontSize: 12,
                padding: "6px 10px",
                width: 110,
                outline: "none",
              }}
            />
          </div>
        }
      />

      {/* Why these picks */}
      <div
        style={{
          padding: "14px 18px",
          background: "var(--purple-bg,var(--blue-bg))",
          border: "1px solid var(--purple,var(--blue))",
          borderRadius: 10,
          fontSize: 12,
          color: "var(--text-secondary)",
          lineHeight: 1.7,
        }}
      >
        <span style={{ color: "var(--purple,var(--blue))", fontWeight: 700 }}>
          How we pick:{" "}
        </span>
        Based on your current holdings, we identify gaps in sector
        diversification, P/E balance, and market-cap spread. Stocks you already
        hold are excluded.
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill,minmax(280px,1fr))",
          gap: 16,
        }}
      >
        {suggestions.map((s, i) => {
          const canBuy = budget >= s.price;
          const qty = Math.floor(budget / s.price);
          const inWish = watchlistSymbols.has(s.symbol);
          return (
            <div
              key={s.symbol}
              style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
                borderRadius: 12,
                padding: 20,
                display: "flex",
                flexDirection: "column",
                gap: 12,
                animation: `fadeUp .4s ease both`,
                animationDelay: `${i * 0.06}s`,
                transition: "border-color .15s, transform .15s",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = "var(--border-light)";
                e.currentTarget.style.transform = "translateY(-2px)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "var(--border)";
                e.currentTarget.style.transform = "none";
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                }}
              >
                <div>
                  <div
                    style={{
                      fontFamily: "var(--mono)",
                      fontSize: 15,
                      fontWeight: 700,
                      color: "var(--text-primary)",
                    }}
                  >
                    {s.symbol}
                  </div>
                  <div
                    style={{
                      fontSize: 11,
                      color: "var(--text-secondary)",
                      marginTop: 2,
                    }}
                  >
                    {s.name}
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div
                    style={{
                      fontFamily: "var(--mono)",
                      fontSize: 14,
                      fontWeight: 600,
                      color: "var(--text-primary)",
                    }}
                  >
                    ₹{s.price.toLocaleString("en-IN")}
                  </div>
                  <span
                    style={{
                      fontSize: 9,
                      padding: "2px 8px",
                      borderRadius: 20,
                      background: "var(--blue-bg)",
                      color: "var(--blue)",
                      fontFamily: "var(--mono)",
                    }}
                  >
                    {s.sector}
                  </span>
                </div>
              </div>

              {/* Score bar */}
              <div>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    fontSize: 10,
                    color: "var(--text-muted)",
                    marginBottom: 5,
                  }}
                >
                  <span style={{ fontFamily: "var(--mono)" }}>
                    AI Match Score
                  </span>
                  <span
                    style={{
                      color: "#8b5cf6",
                      fontFamily: "var(--mono)",
                      fontWeight: 700,
                    }}
                  >
                    {s.score}/100
                  </span>
                </div>
                <div
                  style={{
                    height: 4,
                    background: "var(--border)",
                    borderRadius: 2,
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      height: "100%",
                      width: `${s.score}%`,
                      background: "linear-gradient(90deg,#8b5cf6,#a78bfa)",
                      borderRadius: 2,
                      transition: "width 1.2s cubic-bezier(.4,0,.2,1)",
                    }}
                  />
                </div>
              </div>

              <p
                style={{
                  fontSize: 11,
                  color: "var(--text-secondary)",
                  lineHeight: 1.7,
                  margin: 0,
                }}
              >
                {s.reason}
              </p>

              <div
                style={{
                  fontSize: 10,
                  fontFamily: "var(--mono)",
                  color: canBuy ? "var(--green)" : "var(--amber)",
                }}
              >
                {canBuy
                  ? `✓ Buy ${qty} share${qty !== 1 ? "s" : ""} within ₹${budget.toLocaleString("en-IN")} budget`
                  : `⚠ Above your ₹${budget.toLocaleString("en-IN")} budget`}
              </div>

              <button
                onClick={() => !inWish && onAddWatchlist(s)}
                style={{
                  padding: "8px 0",
                  background: inWish ? "var(--bg-elevated)" : "var(--amber-bg)",
                  border: `1px solid ${inWish ? "var(--border)" : "var(--amber)"}`,
                  borderRadius: 8,
                  color: inWish ? "var(--text-muted)" : "var(--amber)",
                  fontFamily: "var(--mono)",
                  fontSize: 10,
                  cursor: inWish ? "default" : "pointer",
                  letterSpacing: "0.08em",
                  transition: "all .15s",
                }}
              >
                {inWish ? "★ In Watchlist" : "☆ Add to Watchlist"}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// SUB-PAGE: PERSONALISED NEWS
// ═══════════════════════════════════════════════════════════════════════════════
function NewsPage({ holdings, watchlist }) {
  const symbols = new Set([
    ...holdings.map((h) => h.symbol),
    ...watchlist.map((w) => w.symbol),
  ]);
  const [filter, setFilter] = useState("all");

  const news = PERSONALIZED_NEWS.filter(
    (n) => symbols.size === 0 || symbols.has(n.symbol),
  );
  const filtered =
    filter === "all" ? news : news.filter((n) => n.sentiment === filter);

  const sentMap = {
    positive: "var(--green)",
    negative: "var(--red)",
    neutral: "var(--amber)",
  };
  const sentBgMap = {
    positive: "var(--green-bg)",
    negative: "var(--red-bg)",
    neutral: "var(--amber-bg)",
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 20,
        animation: "fadeUp .35s ease both",
      }}
    >
      <PageHeader
        icon={Icon.news}
        title="Personalised News"
        sub={`Latest news for your ${symbols.size} tracked stocks`}
      />

      {/* Filter */}
      <div
        style={{
          display: "flex",
          gap: 4,
          background: "var(--bg-elevated)",
          padding: 3,
          borderRadius: 8,
          width: "fit-content",
          border: "1px solid var(--border)",
        }}
      >
        {[
          ["all", "All"],
          ["positive", "Positive"],
          ["negative", "Negative"],
          ["neutral", "Neutral"],
        ].map(([v, l]) => (
          <button
            key={v}
            onClick={() => setFilter(v)}
            style={{
              padding: "6px 14px",
              background: filter === v ? "var(--bg-card)" : "transparent",
              border: "none",
              borderRadius: 6,
              color: filter === v ? "var(--text-primary)" : "var(--text-muted)",
              fontFamily: "var(--mono)",
              fontSize: 11,
              cursor: "pointer",
              letterSpacing: "0.08em",
              transition: "all .15s",
            }}
          >
            {l}
          </button>
        ))}
      </div>

      {symbols.size === 0 && (
        <div
          style={{
            padding: "14px 18px",
            background: "var(--amber-bg)",
            border: "1px solid var(--amber)",
            borderRadius: 10,
            fontSize: 12,
            color: "var(--amber)",
            fontFamily: "var(--mono)",
          }}
        >
          ⚡ Add holdings or a watchlist to see personalised news.
        </div>
      )}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill,minmax(320px,1fr))",
          gap: 14,
        }}
      >
        {filtered.map((n, i) => (
          <div
            key={n.id}
            style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              borderRadius: 12,
              padding: 20,
              display: "flex",
              flexDirection: "column",
              gap: 10,
              cursor: "pointer",
              animation: `fadeUp .4s ease both`,
              animationDelay: `${i * 0.05}s`,
              transition: "border-color .15s, transform .15s",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "var(--border-light)";
              e.currentTarget.style.transform = "translateY(-2px)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "var(--border)";
              e.currentTarget.style.transform = "none";
            }}
          >
            <div
              style={{
                display: "flex",
                gap: 6,
                alignItems: "center",
                flexWrap: "wrap",
              }}
            >
              <span
                style={{
                  fontSize: 9,
                  padding: "2px 9px",
                  borderRadius: 20,
                  fontFamily: "var(--mono)",
                  fontWeight: 700,
                  letterSpacing: "0.1em",
                  background: sentBgMap[n.sentiment],
                  color: sentMap[n.sentiment],
                  border: `1px solid ${sentMap[n.sentiment]}`,
                }}
              >
                {n.sentiment.toUpperCase()}
              </span>
              <span
                style={{
                  fontSize: 9,
                  padding: "2px 9px",
                  borderRadius: 20,
                  fontFamily: "var(--mono)",
                  background: "var(--blue-bg)",
                  color: "var(--blue)",
                  border: "1px solid var(--blue)",
                }}
              >
                {n.symbol}
              </span>
            </div>
            <h3
              style={{
                fontFamily: "var(--serif)",
                fontSize: 14,
                fontWeight: 600,
                color: "var(--text-primary)",
                lineHeight: 1.45,
                margin: 0,
              }}
            >
              {n.title}
            </h3>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                fontSize: 10,
                color: "var(--text-muted)",
                fontFamily: "var(--mono)",
              }}
            >
              <span>{n.source}</span>
              <span>{n.time}</span>
            </div>
            <p
              style={{
                fontSize: 12,
                color: "var(--text-secondary)",
                lineHeight: 1.6,
                margin: 0,
              }}
            >
              {n.summary}
            </p>
          </div>
        ))}
        {filtered.length === 0 && (
          <div
            style={{
              gridColumn: "1/-1",
              textAlign: "center",
              padding: "40px 20px",
              color: "var(--text-muted)",
              fontSize: 13,
              border: "1px dashed var(--border)",
              borderRadius: 12,
            }}
          >
            No {filter} news found for your holdings.
          </div>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// SIDEBAR
// ═══════════════════════════════════════════════════════════════════════════════
const NAV_ITEMS = [
  { id: "overview", label: "Overview", icon: Icon.grid, color: "var(--green)" },
  { id: "holdings", label: "Holdings", icon: Icon.chart, color: "var(--blue)" },
  { id: "add", label: "Add Holding", icon: Icon.plus, color: "var(--green)" },
  {
    id: "watchlist",
    label: "Watchlist",
    icon: Icon.star,
    color: "var(--amber)",
  },
  { id: "ai", label: "AI Picks", icon: Icon.sparkle, color: "#8b5cf6" },
  { id: "news", label: "News", icon: Icon.news, color: "var(--blue)" },
];

function Sidebar({
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
      {/* Top */}
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

      {/* Nav items */}
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
              <span style={{ flexShrink: 0 }}>{item.icon}</span>
              {!collapsed && <span>{item.label}</span>}
            </button>
          );
        })}
      </nav>

      {/* Back to market */}
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

// ═══════════════════════════════════════════════════════════════════════════════
// ROOT PORTFOLIO PAGE
// ═══════════════════════════════════════════════════════════════════════════════
export default function PortfolioPage({ onBack }) {
  const { user, displayName, avatarInitial } = useAuth();
  const [activePage, setActivePage] = useState("overview");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [holdings, setHoldings] = useState([]);
  const [watchlist, setWatchlist] = useState([]);
  const [loadingData, setLoadingData] = useState(true);

  // ── Fetch portfolio + watchlist from Supabase ────────────────────────────────
  const fetchAll = useCallback(async () => {
    if (!user) return;
    setLoadingData(true);
    const [{ data: ph }, { data: wh }] = await Promise.all([
      supabase
        .from("portfolio")
        .select("*")
        .eq("user_id", user.id)
        .order("created_at", { ascending: false }),
      supabase
        .from("watchlist")
        .select("*")
        .eq("user_id", user.id)
        .order("created_at", { ascending: false }),
    ]);
    if (ph) {
      setHoldings(
        ph.map((h) => ({
          ...h,
          ltp: mockLTP(h.symbol, h.avg_cost),
          currentValue: h.qty * mockLTP(h.symbol, h.avg_cost),
        })),
      );
    }
    if (wh) setWatchlist(wh);
    setLoadingData(false);
  }, [user]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  // ── Delete holding ──────────────────────────────────────────────────────────
  const deleteHolding = async (id) => {
    await supabase.from("portfolio").delete().eq("id", id);
    setHoldings((h) => h.filter((x) => x.id !== id));
  };

  // ── Watchlist add / remove ───────────────────────────────────────────────────
  const addWatchlist = async (stock) => {
    const { data } = await supabase
      .from("watchlist")
      .insert({
        user_id: user.id,
        symbol: stock.symbol,
        name: stock.name || "",
        sector: stock.sector || "",
        price: stock.price || null,
      })
      .select()
      .single();
    if (data) setWatchlist((w) => [data, ...w]);
  };
  const removeWatchlist = async (id) => {
    await supabase.from("watchlist").delete().eq("id", id);
    setWatchlist((w) => w.filter((x) => x.id !== id));
  };

  const renderPage = () => {
    if (loadingData)
      return (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            height: "60vh",
            gap: 16,
          }}
        >
          <div className="spinner" />
          <span
            style={{
              fontFamily: "var(--mono)",
              fontSize: 11,
              color: "var(--text-muted)",
              letterSpacing: "0.15em",
            }}
          >
            Loading your portfolio...
          </span>
        </div>
      );
    switch (activePage) {
      case "overview":
        return (
          <OverviewPage
            holdings={holdings}
            watchlistCount={watchlist.length}
            onNavigate={setActivePage}
          />
        );
      case "holdings":
        return (
          <HoldingsPage
            holdings={holdings}
            onDelete={deleteHolding}
            onNavigateAdd={() => setActivePage("add")}
          />
        );
      case "add":
        return <AddHoldingPage userId={user.id} onSaved={fetchAll} />;
      case "watchlist":
        return (
          <WatchlistPage
            items={watchlist}
            onDelete={removeWatchlist}
            onAdd={addWatchlist}
          />
        );
      case "ai":
        return (
          <AIPicksPage
            holdings={holdings}
            watchlist={watchlist}
            onAddWatchlist={addWatchlist}
          />
        );
      case "news":
        return <NewsPage holdings={holdings} watchlist={watchlist} />;
      default:
        return null;
    }
  };

  return (
    <div
      style={{
        display: "flex",
        minHeight: "100vh",
        background: "var(--bg-primary)",
      }}
    >
      <Sidebar
        active={activePage}
        onNavigate={setActivePage}
        onBack={onBack}
        displayName={displayName}
        avatarInitial={avatarInitial}
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed((c) => !c)}
      />
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          minWidth: 0,
        }}
      >
        {/* Topbar strip */}
        <div
          style={{
            height: 48,
            background: "var(--bg-section)",
            borderBottom: "1px solid var(--border)",
            display: "flex",
            alignItems: "center",
            padding: "0 24px",
            gap: 8,
            flexShrink: 0,
          }}
        >
          <span
            style={{
              fontFamily: "var(--mono)",
              fontSize: 10,
              color: "var(--text-muted)",
              letterSpacing: "0.1em",
            }}
          >
            MARKETLENS
          </span>
          <span style={{ color: "var(--border-light)" }}>›</span>
          <span
            style={{
              fontFamily: "var(--mono)",
              fontSize: 10,
              color: "var(--green)",
              letterSpacing: "0.1em",
            }}
          >
            PORTFOLIO
          </span>
          <span style={{ color: "var(--border-light)" }}>›</span>
          <span
            style={{
              fontFamily: "var(--mono)",
              fontSize: 10,
              color: "var(--text-secondary)",
              letterSpacing: "0.1em",
              textTransform: "uppercase",
            }}
          >
            {NAV_ITEMS.find((n) => n.id === activePage)?.label}
          </span>
        </div>
        {/* Page content */}
        <main
          style={{
            flex: 1,
            padding: "28px 32px 48px",
            overflowY: "auto",
            maxWidth: 1200,
          }}
        >
          {renderPage()}
        </main>
        <footer
          style={{
            padding: "12px 32px",
            borderTop: "1px solid var(--border)",
            fontFamily: "var(--mono)",
            fontSize: 10,
            color: "var(--text-muted)",
            letterSpacing: "0.06em",
          }}
        >
          For informational purposes only. Not financial advice.
        </footer>
      </div>
    </div>
  );
}
