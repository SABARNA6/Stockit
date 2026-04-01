import { useState, useEffect, useCallback, useRef } from "react";
import { stockApi } from "../api/stockApi";

// Simple in-memory cache: { key: { data, ts } }
const CACHE = {};
const CACHE_MAX_SIZE = 200;
const TTL = {
  overview: 60_000,
  sparkline: 60_000,
  chart: 60_000,
  volume: 60_000,
  trends: 90_000,
  recommendation: 120_000,
  fundamentals: 3_600_000,
  news: 900_000,
  historical: 300_000,
  search: 120_000,
};

const RECENT_SEARCH_KEY = "stockit.recentSearches.v1";
const RECENT_SEARCH_LIMIT = 5;
const POPULAR_SUGGESTIONS = [
  {
    symbol: "RELIANCE",
    name: "Reliance Industries Ltd",
    exchange: "NSE",
    matchedOn: "popular",
  },
  {
    symbol: "TCS",
    name: "Tata Consultancy Services Ltd",
    exchange: "NSE",
    matchedOn: "popular",
  },
  {
    symbol: "INFY",
    name: "Infosys Ltd",
    exchange: "NSE",
    matchedOn: "popular",
  },
  {
    symbol: "HDFCBANK",
    name: "HDFC Bank Ltd",
    exchange: "NSE",
    matchedOn: "popular",
  },
  {
    symbol: "ICICIBANK",
    name: "ICICI Bank Ltd",
    exchange: "NSE",
    matchedOn: "popular",
  },
];

function readRecentSearches() {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(RECENT_SEARCH_KEY);
    const parsed = JSON.parse(raw || "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeRecentSearches(items) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(
      RECENT_SEARCH_KEY,
      JSON.stringify(items.slice(0, RECENT_SEARCH_LIMIT)),
    );
  } catch {
    // Ignore storage failures in private mode/strict browsers.
  }
}

function cached(key, ttl, fn, signal) {
  const hit = CACHE[key];
  if (hit && Date.now() - hit.ts < ttl) return Promise.resolve(hit.data);
  return fn(signal).then((data) => {
    if (Object.keys(CACHE).length >= CACHE_MAX_SIZE) {
      let oldestKey = null;
      let oldestTs = Infinity;
      for (const k in CACHE) {
        if (CACHE[k].ts < oldestTs) {
          oldestTs = CACHE[k].ts;
          oldestKey = k;
        }
      }
      if (oldestKey) delete CACHE[oldestKey];
    }
    CACHE[key] = { data, ts: Date.now() };
    return data;
  });
}

// ─── useStockData ─────────────────────────────────────────────────────────────
export function useStockData(symbol) {
  const [state, setState] = useState({
    overview: null,
    sparkline: null,
    trends: null,
    recommendation: null,
    loading: true,
    error: null,
  });

  const load = useCallback(async (sym, signal) => {
    if (!sym) return;
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const overview = await cached(`overview:${sym}`, TTL.overview, () =>
        stockApi.overview(sym), signal);

      if (signal?.aborted) return;

      if (!overview) {
        setState((s) => ({
          ...s,
          loading: false,
          error: `Symbol '${sym}' not found`,
        }));
        return;
      }

      const [sparkline, trends, recommendation] = await Promise.all([
        cached(`sparkline:${sym}`, TTL.sparkline, () =>
          stockApi.sparkline(sym, 14), signal),
        cached(`trends:${sym}`, TTL.trends, () => stockApi.trends(sym), signal),
        cached(`recommendation:${sym}`, TTL.recommendation, () =>
          stockApi.recommendation(sym), signal),
      ]);

      if (signal?.aborted) return;

      setState({
        overview,
        sparkline,
        trends,
        recommendation,
        loading: false,
        error: null,
      });
    } catch (e) {
      if (signal?.aborted) return;
      if (e.name === "AbortError") return;
      setState((s) => ({ ...s, loading: false, error: e.message }));
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    load(symbol, controller.signal);
    return () => controller.abort(); // Cancel on symbol change
  }, [symbol, load]);

  return { ...state, reload: () => load(symbol) };
}

// ─── useChart ─────────────────────────────────────────────────────────────────
export function useChart(symbol, timeframe) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Clear cache when symbol or timeframe changes
  useEffect(() => {
    const key = `chart:${symbol}:${timeframe}`;
    delete CACHE[key];
    // console.log(`[useChart] Cache cleared for key: ${key}`);
  }, [symbol, timeframe]);

  useEffect(() => {
    if (!symbol) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    const key = `chart:${symbol}:${timeframe}`;

    // Fetch fresh data directly (skip cache to ensure fresh data)
    Promise.all([
      stockApi.chart(symbol, timeframe).catch((err) => {
        console.error(`[useChart] chart API failed for ${symbol}:`, err);
        return { candles: [] };
      }),
      stockApi.volume(symbol, timeframe).catch((err) => {
        console.error(`[useChart] volume API failed for ${symbol}:`, err);
        return { volumes: [], avgVolume: 0 };
      }),
    ])
      .then(([c, v]) => {
        // console.log(
        //   `[useChart] Received API data: ${c?.candles?.length || 0} candles, ${v?.volumes?.length || 0} volumes`,
        // );

        // Align volumes with candles by timestamp to prevent misalignment
        const candles = c?.candles || [];
        const volumesMap = {};
        (v?.volumes || []).forEach((vol) => {
          if (vol?.timestamp) {
            volumesMap[vol.timestamp] = vol;
          }
        });

        // Reconstruct volumes array aligned with candles
        const alignedVolumes = candles.map(
          (candle) =>
            volumesMap[candle.timestamp] || {
              timestamp: candle.timestamp,
              volume: 0,
            },
        );

        // console.log(
        //   `[useChart] Aligned volumes: ${alignedVolumes.length} entries aligned with ${candles.length} candles`,
        // );

        return {
          candles,
          volumes: alignedVolumes,
          avgVolume: v?.avgVolume || 0,
        };
      })
      .then((d) => {
        if (cancelled) return;
        // console.log(`[useChart] Setting chart data for ${symbol}:`, {
        //   candles: d.candles?.length,
        //   volumes: d.volumes?.length,
        //   avgVolume: d.avgVolume,
        // });
        setData(d);
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        console.error(`[useChart] Fatal error for ${symbol}:`, err);
        setError(err);
        setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [symbol, timeframe]);

  return { data, loading, error };
}

// ─── useFundamentals ──────────────────────────────────────────────────────────
export function useFundamentals(symbol) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!symbol) return;
    const controller = new AbortController();
    let cancelled = false;
    setLoading(true);
    cached(`fundamentals:${symbol}`, TTL.fundamentals, () =>
      stockApi.fundamentals(symbol), controller.signal)
      .then((d) => {
        if (cancelled) return;
        setData(d);
        setLoading(false);
      })
      .catch(() => {
        if (cancelled) return;
        setLoading(false);
      });

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [symbol]);

  return { data, loading };
}

// ─── useNews ──────────────────────────────────────────────────────────────────
export function useNews(symbol) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!symbol) return;
    const controller = new AbortController();
    let cancelled = false;
    setLoading(true);
    cached(`news:${symbol}`, TTL.news, () => stockApi.news(symbol), controller.signal)
      .then((d) => {
        if (cancelled) return;
        setData(d);
        setLoading(false);
      })
      .catch(() => {
        if (cancelled) return;
        setLoading(false);
      });

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [symbol]);

  return { data, loading };
}

// ─── useHistorical ────────────────────────────────────────────────────────────
export function useHistorical(symbol, period, page) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!symbol) return;
    const controller = new AbortController();
    let cancelled = false;
    setLoading(true);
    const key = `hist:${symbol}:${period}:${page}`;
    cached(key, TTL.historical, () => stockApi.historical(symbol, period, page), controller.signal)
      .then((d) => {
        if (cancelled) return;
        setData(d);
        setLoading(false);
      })
      .catch(() => {
        if (cancelled) return;
        setLoading(false);
      });

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [symbol, period, page]);

  return { data, loading };
}

// ─── useSearch ────────────────────────────────────────────────────────────────
export function useSearch() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [recent, setRecent] = useState(() => readRecentSearches());
  const timer = useRef(null);
  const requestSeq = useRef(0);

  const emptySuggestions = useCallback(() => {
    const seen = new Set();
    const merged = [];
    for (const item of [...recent, ...POPULAR_SUGGESTIONS]) {
      const key = `${item.symbol}:${item.exchange || ""}`;
      if (seen.has(key)) continue;
      seen.add(key);
      merged.push(item);
    }
    return merged.slice(0, 8);
  }, [recent]);

  const addRecentSearch = useCallback((item) => {
    const symbol = String(item?.symbol || "")
      .trim()
      .toUpperCase();
    if (!symbol) return;

    const normalized = {
      symbol,
      name: item?.name || symbol,
      exchange: item?.exchange || "NSE",
      matchedOn: "recent",
    };

    setRecent((prev) => {
      const next = [
        normalized,
        ...prev.filter(
          (entry) => String(entry?.symbol || "").toUpperCase() !== symbol,
        ),
      ].slice(0, RECENT_SEARCH_LIMIT);
      writeRecentSearches(next);
      return next;
    });
  }, []);

  useEffect(() => {
    setResults(emptySuggestions());
  }, [emptySuggestions]);

  useEffect(() => {
    return () => clearTimeout(timer.current);
  }, []);

  const search = useCallback(
    (q) => {
      setQuery(q);
      clearTimeout(timer.current);

      const normalized = String(q || "")
        .trim()
        .toUpperCase();
      if (!normalized || normalized.length < 2) {
        setResults(emptySuggestions());
        setLoading(false);
        return;
      }

      const cacheKey = `search:${normalized}`;
      const hit = CACHE[cacheKey];
      if (hit && Date.now() - hit.ts < TTL.search) {
        setResults(hit.data || []);
        setLoading(false);
        return;
      }

      timer.current = setTimeout(async () => {
        const currentRequest = ++requestSeq.current;
        setLoading(true);
        try {
          const r = await stockApi.search(normalized, 10);
          if (currentRequest !== requestSeq.current) return;
          const nextResults = r.data || [];
          CACHE[cacheKey] = { data: nextResults, ts: Date.now() };
          setResults(nextResults);
        } catch {
          if (currentRequest !== requestSeq.current) return;
          setResults([]);
        } finally {
          if (currentRequest === requestSeq.current) {
            setLoading(false);
          }
        }
      }, 350);
    },
    [emptySuggestions],
  );

  return { query, results, loading, search, addRecentSearch };
}
