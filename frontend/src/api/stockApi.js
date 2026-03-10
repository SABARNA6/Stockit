// ─── CONFIG ─────────────────────────────────────────────────────────────────
const BASE =
  typeof window !== "undefined"
    ? window.STOCK_API_BASE || "http://localhost:10000/api"
    : "/api";

async function apiFetch(path) {
  const fullUrl = `${BASE}${path}`;
  console.error(`[apiFetch] Calling: ${fullUrl}`);
  try {
    const res = await fetch(fullUrl);
    if (!res.ok) {
      console.error(`[apiFetch] HTTP ${res.status} from ${fullUrl}`);
      throw new Error(`API ${res.status}: ${path}`);
    }
    const data = await res.json();
    return data;
  } catch (err) {
    console.error(`[apiFetch] Failed to fetch ${fullUrl}:`, err.message);
    throw err;
  }
}

// ─── ENDPOINTS ───────────────────────────────────────────────────────────────
export const stockApi = {
  overview: (symbol) => apiFetch(`/stocks/${symbol}`).then((r) => r.data),
  sparkline: (symbol, points = 12) =>
    apiFetch(`/stocks/${symbol}/sparkline?points=${points}`).then(
      (r) => r.data,
    ),
  chart: (symbol, timeframe = "3M") =>
    apiFetch(`/stocks/${symbol}/chart?timeframe=${timeframe}`).then(
      (r) => r.data,
    ),
  volume: (symbol, timeframe = "3M") =>
    apiFetch(`/stocks/${symbol}/volume?timeframe=${timeframe}`).then(
      (r) => r.data,
    ),
  trends: (symbol) => apiFetch(`/stocks/${symbol}/trends`).then((r) => r.data),
  recommendation: (symbol) =>
    apiFetch(`/stocks/${symbol}/recommendation`).then((r) => r.data),
  fundamentals: (symbol) =>
    apiFetch(`/stocks/${symbol}/fundamentals`).then((r) => r.data),
  news: (symbol) => apiFetch(`/stocks/${symbol}/news`).then((r) => r.data),
  historical: (symbol, period = "1mo", page = 1, limit = 8) =>
    apiFetch(
      `/stocks/${symbol}/historical?period=${period}&page=${page}&limit=${limit}`,
    ).then((r) => r.data),
  search: (symbol) => apiFetch(`/company/search?symbol=${symbol}`),
};

// ─── FORMATTERS ──────────────────────────────────────────────────────────────
export const fmt = {
  price: (v) =>
    v == null
      ? "—"
      : "₹" + Number(v).toLocaleString("en-IN", { maximumFractionDigits: 2 }),
  pct: (v) =>
    v == null ? "—" : (v >= 0 ? "+" : "") + Number(v).toFixed(2) + "%",
  crore: (v) => {
    if (v == null) return "—";
    const cr = v / 1e7;
    if (cr >= 1e5) return "₹" + (cr / 1e5).toFixed(2) + "L Cr";
    if (cr >= 1e3) return "₹" + (cr / 1e3).toFixed(1) + "K Cr";
    return "₹" + cr.toFixed(0) + " Cr";
  },
  ratio: (v, s = "×") => (v == null ? "—" : Number(v).toFixed(2) + s),
  num: (v, d = 1) => (v == null ? "—" : Number(v).toFixed(d)),
  vol: (v) => {
    if (v == null) return "—";
    if (v >= 1e7) return (v / 1e7).toFixed(1) + "Cr";
    if (v >= 1e5) return (v / 1e5).toFixed(1) + "L";
    if (v >= 1e3) return (v / 1e3).toFixed(1) + "K";
    return String(v);
  },
  date: (s) => {
    if (!s) return "—";
    return new Date(s).toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  },
};
