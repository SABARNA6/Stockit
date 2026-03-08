import { useState, useEffect, useCallback, useRef } from "react";
import { stockApi } from "../api/stockApi";

// Simple in-memory cache: { key: { data, ts } }
const CACHE = {};
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
};

function cached(key, ttl, fn) {
  const hit = CACHE[key];
  if (hit && Date.now() - hit.ts < ttl) return Promise.resolve(hit.data);
  return fn().then((data) => {
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
      // First, validate that symbol exists
      const overview = await cached(`overview:${sym}`, TTL.overview, () =>
        stockApi.overview(sym),
      );

      if (signal?.aborted) return; // Ignore if symbol changed

      // If overview is null or empty, symbol doesn't exist
      if (!overview) {
        setState((s) => ({
          ...s,
          loading: false,
          error: `Symbol '${sym}' not found`,
        }));
        return;
      }

      // Symbol exists, now fetch other data in parallel
      const [sparkline, trends, recommendation] = await Promise.all([
        cached(`sparkline:${sym}`, TTL.sparkline, () =>
          stockApi.sparkline(sym, 14),
        ),
        cached(`trends:${sym}`, TTL.trends, () => stockApi.trends(sym)),
        cached(`recommendation:${sym}`, TTL.recommendation, () =>
          stockApi.recommendation(sym),
        ),
      ]);

      if (signal?.aborted) return; // Ignore if symbol changed

      setState({
        overview,
        sparkline,
        trends,
        recommendation,
        loading: false,
        error: null,
      });
    } catch (e) {
      if (signal?.aborted) return; // Ignore if symbol changed
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
    let cancelled = false;
    setLoading(true);
    cached(`fundamentals:${symbol}`, TTL.fundamentals, () =>
      stockApi.fundamentals(symbol),
    )
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
    let cancelled = false;
    setLoading(true);
    cached(`news:${symbol}`, TTL.news, () => stockApi.news(symbol))
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
    let cancelled = false;
    setLoading(true);
    const key = `hist:${symbol}:${period}:${page}`;
    cached(key, TTL.historical, () => stockApi.historical(symbol, period, page))
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
    };
  }, [symbol, period, page]);

  return { data, loading };
}

// ─── useSearch ────────────────────────────────────────────────────────────────
export function useSearch() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const timer = useRef(null);

  const search = useCallback((q) => {
    setQuery(q);
    clearTimeout(timer.current);
    if (!q || q.length < 2) {
      setResults([]);
      return;
    }
    timer.current = setTimeout(async () => {
      setLoading(true);
      try {
        const r = await stockApi.search(q.toUpperCase());
        setResults(r.data || []);
      } catch {
        setResults([]);
      }
      setLoading(false);
    }, 350);
  }, []);

  return { query, results, loading, search };
}
