// ─── Icons ──────────────────────────────────────────────────────────
export const Icon = {
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

// ─── Mock Data ──────────────────────────────────────────────────────
export const MOCK_PRICES = {
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

export const AI_SUGGESTIONS = [
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

export const PERSONALIZED_NEWS = [
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

export const PIE_COLORS = [
  "#3b82f6",
  "#10d68e",
  "#8b5cf6",
  "#f0a030",
  "#f04060",
  "#06b6d4",
  "#f472b6",
  "#a3e635",
];

export const NAV_ITEMS = [
  { id: "overview", label: "Overview", icon: "grid", color: "var(--green)" },
  { id: "holdings", label: "Holdings", icon: "chart", color: "var(--blue)" },
  { id: "add", label: "Add Holding", icon: "plus", color: "var(--green)" },
  { id: "watchlist", label: "Watchlist", icon: "star", color: "var(--amber)" },
  { id: "ai", label: "AI Picks", icon: "sparkle", color: "#8b5cf6" },
  { id: "news", label: "News", icon: "news", color: "var(--blue)" },
];

// ─── Helpers ────────────────────────────────────────────────────────
export const mockLTP = (sym, avg) =>
  MOCK_PRICES[sym] || avg * (0.85 + Math.random() * 0.4);

export const getAISignal = (sym, avg, ltp) => {
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
};
