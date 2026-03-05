import { useState, useEffect, useCallback, useRef } from "react";
import { stockApi } from "../api/stockApi";

// Simple in-memory cache: { key: { data, ts } }
const CACHE = {};
const TTL = {
  overview:       60_000,
  sparkline:      60_000,
  chart:          60_000,
  volume:         60_000,
  trends:         90_000,
  recommendation: 120_000,
  fundamentals:   3_600_000,
  news:           900_000,
  historical:     300_000,
};

function cached(key, ttl, fn) {
  const hit = CACHE[key];
  if (hit && Date.now() - hit.ts < ttl) return Promise.resolve(hit.data);
  return fn().then(data => { CACHE[key] = { data, ts: Date.now() }; return data; });
}

// ─── useStockData ─────────────────────────────────────────────────────────────
export function useStockData(symbol) {
  const [state, setState] = useState({
    overview: null, sparkline: null, trends: null,
    recommendation: null, loading: true, error: null,
  });

  const load = useCallback(async (sym) => {
    if (!sym) return;
    setState(s => ({ ...s, loading: true, error: null }));
    try {
      const [overview, sparkline, trends, recommendation] = await Promise.all([
        cached(`overview:${sym}`,       TTL.overview,       () => stockApi.overview(sym)),
        cached(`sparkline:${sym}`,      TTL.sparkline,      () => stockApi.sparkline(sym, 14)),
        cached(`trends:${sym}`,         TTL.trends,         () => stockApi.trends(sym)),
        cached(`recommendation:${sym}`, TTL.recommendation, () => stockApi.recommendation(sym)),
      ]);
      setState({ overview, sparkline, trends, recommendation, loading: false, error: null });
    } catch (e) {
      setState(s => ({ ...s, loading: false, error: e.message }));
    }
  }, []);

  useEffect(() => { load(symbol); }, [symbol, load]);
  return { ...state, reload: () => load(symbol) };
}

// ─── useChart ─────────────────────────────────────────────────────────────────
export function useChart(symbol, timeframe) {
  const [data, setData]     = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!symbol) return;
    setLoading(true);
    const key = `chart:${symbol}:${timeframe}`;
    cached(key, TTL.chart, () =>
      Promise.all([stockApi.chart(symbol, timeframe), stockApi.volume(symbol, timeframe)])
        .then(([c, v]) => ({ candles: c.candles, volumes: v.volumes, avgVolume: v.avgVolume }))
    ).then(d => { setData(d); setLoading(false); })
     .catch(() => setLoading(false));
  }, [symbol, timeframe]);

  return { data, loading };
}

// ─── useFundamentals ──────────────────────────────────────────────────────────
export function useFundamentals(symbol) {
  const [data, setData]     = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!symbol) return;
    setLoading(true);
    cached(`fundamentals:${symbol}`, TTL.fundamentals, () => stockApi.fundamentals(symbol))
      .then(d => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [symbol]);

  return { data, loading };
}

// ─── useNews ──────────────────────────────────────────────────────────────────
export function useNews(symbol) {
  const [data, setData]     = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!symbol) return;
    setLoading(true);
    cached(`news:${symbol}`, TTL.news, () => stockApi.news(symbol))
      .then(d => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [symbol]);

  return { data, loading };
}

// ─── useHistorical ────────────────────────────────────────────────────────────
export function useHistorical(symbol, period, page) {
  const [data, setData]     = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!symbol) return;
    setLoading(true);
    const key = `hist:${symbol}:${period}:${page}`;
    cached(key, TTL.historical, () => stockApi.historical(symbol, period, page))
      .then(d => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [symbol, period, page]);

  return { data, loading };
}

// ─── useSearch ────────────────────────────────────────────────────────────────
export function useSearch() {
  const [query, setQuery]   = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const timer = useRef(null);

  const search = useCallback((q) => {
    setQuery(q);
    clearTimeout(timer.current);
    if (!q || q.length < 2) { setResults([]); return; }
    timer.current = setTimeout(async () => {
      setLoading(true);
      try {
        const r = await stockApi.search(q.toUpperCase());
        setResults(r.data || []);
      } catch { setResults([]); }
      setLoading(false);
    }, 350);
  }, []);

  return { query, results, loading, search };
}
