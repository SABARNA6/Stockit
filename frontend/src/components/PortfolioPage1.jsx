// frontend/src/pages/PortfolioPage.jsx
//
// FULLY INTEGRATED — replaces all mock data with real API calls:
//
//  DATA SOURCE          BEFORE (mock)              AFTER (real)
//  ─────────────────────────────────────────────────────────────
//  Holdings             Supabase direct             GET /api/portfolio
//  Live prices (ltp)    mockLTP()                   GET /api/stocks/<symbol>
//  currentValue         qty × mockLTP               qty × real ltp
//  AI picks             AI_SUGGESTIONS mock          POST /api/ml/recommend
//  Portfolio news       PERSONALIZED_NEWS mock       GET /api/stocks/<symbol>/news
//  Watchlist            Supabase direct             GET /api/watchlist
//  Health score         hardcoded                   computed from real P&L + diversification
//  Add holding          Supabase direct             POST /api/portfolio
//  Delete holding       Supabase direct             DELETE /api/portfolio/<id>
//  Add watchlist        Supabase direct             POST /api/watchlist
//  Remove watchlist     Supabase direct             DELETE /api/watchlist/<id>

import { useState, useEffect, useCallback, useRef } from "react";
import { useAuth } from "../context/AuthContext";
import { supabase } from "../supabaseClient";

// Sub-pages (these remain as-is — they just receive real data via props)
import Sidebar from "./portfolio/common/Sidebar";
import OverviewPage from "./portfolio/pages/Overview";
import HoldingsPage from "./portfolio/pages/Holdings";
import AddHoldingPage from "./portfolio/pages/AddHolding";
import WatchlistPage from "./portfolio/pages/Watchlist";
import AIPicksPage from "./portfolio/pages/AIPicks";
import NewsPage from "./portfolio/pages/News";
import { NAV_ITEMS } from "./portfolio/utils";

// ─────────────────────────────────────────────────────────────────────────────
// CONFIG
// ─────────────────────────────────────────────────────────────────────────────
const API = window.STOCK_API_BASE || "/api";

// How long to cache live prices before re-fetching (ms)
const PRICE_CACHE_TTL = 60_000; // 1 minute

// ─────────────────────────────────────────────────────────────────────────────
// API HELPERS
// ─────────────────────────────────────────────────────────────────────────────

/** Get Authorization header from current Supabase session */
async function authHeaders() {
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session?.access_token) throw new Error("Not logged in");
  return {
    Authorization: `Bearer ${session.access_token}`,
    "Content-Type": "application/json",
  };
}

/** Fetch from Flask backend with auth */
async function apiFetch(path, options = {}) {
  const headers = await authHeaders();
  const res = await fetch(`${API}${path}`, {
    ...options,
    headers: { ...headers, ...(options.headers || {}) },
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  const json = await res.json();
  // backend returns { success, data } or { data }
  return json.data ?? json;
}

/** Fetch live price for one symbol. Returns currentPrice or null. */
async function fetchLivePrice(symbol) {
  try {
    const data = await apiFetch(`/stocks/${symbol}`);
    return data?.currentPrice ?? null;
  } catch {
    return null;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// HEALTH SCORE  (0–100, computed from real data)
// ─────────────────────────────────────────────────────────────────────────────
function computeHealthScore(holdings) {
  if (!holdings.length) return 0;

  let score = 55;

  // Diversification: more holdings = better (up to +20)
  score += Math.min(holdings.length * 5, 20);

  // Concentration penalty: single holding > 50% of portfolio
  const total = holdings.reduce((s, h) => s + (h.currentValue || 0), 0);
  if (total > 0) {
    const maxWeight = Math.max(
      ...holdings.map((h) => (h.currentValue || 0) / total),
    );
    if (maxWeight > 0.6) score -= 20;
    else if (maxWeight > 0.4) score -= 10;
  }

  // P&L health: overall gain/loss
  const totalInvested = holdings.reduce((s, h) => s + h.qty * h.avg_cost, 0);
  const totalCurrent = holdings.reduce((s, h) => s + (h.currentValue || 0), 0);
  if (totalInvested > 0) {
    const pnlPct = ((totalCurrent - totalInvested) / totalInvested) * 100;
    if (pnlPct > 15) score += 15;
    else if (pnlPct > 5) score += 8;
    else if (pnlPct < -15) score -= 15;
    else if (pnlPct < -5) score -= 8;
  }

  return Math.min(100, Math.max(0, Math.round(score)));
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN COMPONENT
// ─────────────────────────────────────────────────────────────────────────────
export default function PortfolioPage({ onBack }) {
  const { user, displayName, avatarInitial } = useAuth();

  // ── UI state ──────────────────────────────────────────────────────────────
  const [activePage, setActivePage] = useState("overview");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // ── Data state ────────────────────────────────────────────────────────────
  const [holdings, setHoldings] = useState([]);
  const [watchlist, setWatchlist] = useState([]);
  const [aiPicks, setAiPicks] = useState(null); // ML recommendations
  const [portfolioNews, setPortfolioNews] = useState([]); // news for held stocks

  // ── Loading / error state ─────────────────────────────────────────────────
  const [loadingData, setLoadingData] = useState(true);
  const [loadingPrices, setLoadingPrices] = useState(false);
  const [loadingAI, setLoadingAI] = useState(false);
  const [loadingNews, setLoadingNews] = useState(false);
  const [error, setError] = useState(null);

  // ── Price cache (symbol → { price, timestamp }) ───────────────────────────
  const priceCache = useRef({});

  // ══════════════════════════════════════════════════════════════════════════
  // 1. FETCH HOLDINGS + WATCHLIST (from Flask /api/portfolio and /api/watchlist)
  // ══════════════════════════════════════════════════════════════════════════
  const fetchPortfolioAndWatchlist = useCallback(async () => {
    if (!user) return;
    setLoadingData(true);
    setError(null);

    try {
      const [rawHoldings, rawWatchlist] = await Promise.all([
        apiFetch("/portfolio"),
        apiFetch("/watchlist"),
      ]);

      // Holdings without live price yet — set ltp = avg_cost as placeholder
      const holdingsBase = (rawHoldings || []).map((h) => ({
        ...h,
        ltp: h.avg_cost, // placeholder until live price arrives
        currentValue: h.qty * h.avg_cost, // placeholder
        priceLoaded: false,
      }));

      setHoldings(holdingsBase);
      setWatchlist(rawWatchlist || []);
      setLoadingData(false);

      // Now fetch live prices in the background
      if (holdingsBase.length > 0) {
        fetchLivePrices(holdingsBase);
      }
    } catch (err) {
      console.error("[fetchPortfolioAndWatchlist]", err);
      setError(err.message);
      setLoadingData(false);
    }
  }, [user]);

  // ══════════════════════════════════════════════════════════════════════════
  // 2. FETCH LIVE PRICES  (GET /api/stocks/<symbol> for each holding)
  // ══════════════════════════════════════════════════════════════════════════
  const fetchLivePrices = useCallback(async (holdingsToPrice) => {
    setLoadingPrices(true);
    const now = Date.now();

    // Batch price fetches, respecting cache
    const updates = await Promise.all(
      holdingsToPrice.map(async (h) => {
        const cached = priceCache.current[h.symbol];
        if (cached && now - cached.timestamp < PRICE_CACHE_TTL) {
          return { id: h.id, symbol: h.symbol, ltp: cached.price };
        }
        const price = await fetchLivePrice(h.symbol);
        if (price != null) {
          priceCache.current[h.symbol] = { price, timestamp: now };
        }
        return { id: h.id, symbol: h.symbol, ltp: price };
      }),
    );

    // Merge live prices back into holdings
    setHoldings((prev) =>
      prev.map((h) => {
        const update = updates.find((u) => u.id === h.id);
        if (!update || update.ltp == null) return { ...h, priceLoaded: true };
        return {
          ...h,
          ltp: update.ltp,
          currentValue: h.qty * update.ltp,
          pnl: (update.ltp - h.avg_cost) * h.qty,
          pnlPct: ((update.ltp - h.avg_cost) / h.avg_cost) * 100,
          priceLoaded: true,
        };
      }),
    );

    setLoadingPrices(false);
  }, []);

  // ══════════════════════════════════════════════════════════════════════════
  // 3. FETCH AI PICKS  (POST /api/ml/recommend)
  // Called lazily when user visits the AI Picks page
  // ══════════════════════════════════════════════════════════════════════════
  const fetchAIPicks = useCallback(async () => {
    if (!holdings.length || aiPicks) return; // already loaded or no holdings
    setLoadingAI(true);

    try {
      const portfolio = holdings.map((h) => ({
        ticker: h.symbol,
        market_value: h.currentValue || h.qty * h.avg_cost,
      }));

      const result = await apiFetch("/ml/recommend", {
        method: "POST",
        body: JSON.stringify({
          portfolio,
          risk_profile: "Medium",
          top_k: 5,
          run_backtest: true,
        }),
      });

      setAiPicks(result);
    } catch (err) {
      console.error("[fetchAIPicks]", err);
      setAiPicks({ error: err.message });
    } finally {
      setLoadingAI(false);
    }
  }, [holdings, aiPicks]);

  // ══════════════════════════════════════════════════════════════════════════
  // 4. FETCH PORTFOLIO NEWS  (GET /api/stocks/<symbol>/news for top holdings)
  // Called lazily when user visits the News page
  // ══════════════════════════════════════════════════════════════════════════
  const fetchPortfolioNews = useCallback(async () => {
    if (!holdings.length || portfolioNews.length) return;

    setLoadingNews(true);

    // Normalize symbol: strip .NS / .BO suffix for news lookup
    // (news API uses company name search, not exchange suffix)
    // Also deduplicate: TCS.NS and TCS are the same company
    const normalizeForNews = (symbol) => symbol.replace(/\.(NS|BO|L|TO)$/i, "");

    // Deduplicate by normalized symbol, then take top 3 by value
    const seen = new Set();
    const top3 = [...holdings]
      .sort((a, b) => (b.currentValue || 0) - (a.currentValue || 0))
      .filter((h) => {
        const normalized = normalizeForNews(h.symbol);
        if (seen.has(normalized)) return false;
        seen.add(normalized);
        return true;
      })
      .slice(0, 3);

    try {
      const newsResults = await Promise.all(
        top3.map(async (h) => {
          // Use the original symbol for the API call (backend handles .NS lookup)
          const displaySymbol = normalizeForNews(h.symbol);
          try {
            const data = await apiFetch(`/stocks/${h.symbol}/news`);
            return {
              symbol: displaySymbol,
              news: data?.news || [],
              sentiment: data?.sentiment || {},
            };
          } catch {
            return { symbol: displaySymbol, news: [], sentiment: {} };
          }
        }),
      );
      setPortfolioNews(newsResults);
    } catch (err) {
      console.error("[fetchPortfolioNews]", err);
    } finally {
      setLoadingNews(false);
    }
  }, [holdings, portfolioNews]);

  // ══════════════════════════════════════════════════════════════════════════
  // MUTATIONS
  // ══════════════════════════════════════════════════════════════════════════

  const deleteHolding = async (id) => {
    try {
      await apiFetch(`/portfolio/${id}`, { method: "DELETE" });
      setHoldings((h) => h.filter((x) => x.id !== id));
    } catch (err) {
      console.error("[deleteHolding]", err);
    }
  };

  const addWatchlist = async (stock) => {
    try {
      const data = await apiFetch("/watchlist", {
        method: "POST",
        body: JSON.stringify({
          symbol: stock.symbol,
          name: stock.name || "",
          sector: stock.sector || "",
          price: stock.price || null,
          target_price: stock.target_price || null,
          note: stock.note || null,
        }),
      });
      if (data) setWatchlist((w) => [data, ...w]);
    } catch (err) {
      // 409 = already in watchlist — surface to user
      console.error("[addWatchlist]", err);
    }
  };

  const removeWatchlist = async (id) => {
    try {
      await apiFetch(`/watchlist/${id}`, { method: "DELETE" });
      setWatchlist((w) => w.filter((x) => x.id !== id));
    } catch (err) {
      console.error("[removeWatchlist]", err);
    }
  };

  // Callback for AddHoldingPage after saving — re-fetch everything
  const onHoldingSaved = useCallback(async () => {
    await fetchPortfolioAndWatchlist();
    setActivePage("holdings");
  }, [fetchPortfolioAndWatchlist]);

  // ══════════════════════════════════════════════════════════════════════════
  // EFFECTS
  // ══════════════════════════════════════════════════════════════════════════

  // Initial load
  useEffect(() => {
    fetchPortfolioAndWatchlist();
  }, [fetchPortfolioAndWatchlist]);

  // Lazy-load AI picks + news when those pages are visited
  useEffect(() => {
    if (activePage === "ai") fetchAIPicks();
    if (activePage === "news") fetchPortfolioNews();
  }, [activePage, fetchAIPicks, fetchPortfolioNews]);

  // ══════════════════════════════════════════════════════════════════════════
  // DERIVED DATA (passed into sub-pages)
  // ══════════════════════════════════════════════════════════════════════════
  const totalInvested = holdings.reduce((s, h) => s + h.qty * h.avg_cost, 0);
  const totalCurrent = holdings.reduce((s, h) => s + (h.currentValue || 0), 0);
  const totalPnL = totalCurrent - totalInvested;
  const totalPnLPct = totalInvested > 0 ? (totalPnL / totalInvested) * 100 : 0;
  const healthScore = computeHealthScore(holdings);

  // ══════════════════════════════════════════════════════════════════════════
  // RENDER
  // ══════════════════════════════════════════════════════════════════════════

  const renderPage = () => {
    if (loadingData) {
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
    }

    if (error) {
      return (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            height: "60vh",
            gap: 12,
          }}
        >
          <span style={{ fontSize: 24 }}>⚠️</span>
          <span
            style={{
              fontFamily: "var(--mono)",
              fontSize: 12,
              color: "var(--text-muted)",
            }}
          >
            {error}
          </span>
          <button
            onClick={fetchPortfolioAndWatchlist}
            style={{
              padding: "8px 16px",
              background: "var(--green)",
              color: "#000",
              border: "none",
              borderRadius: 6,
              fontFamily: "var(--mono)",
              fontSize: 11,
              cursor: "pointer",
            }}
          >
            Retry
          </button>
        </div>
      );
    }

    switch (activePage) {
      case "overview":
        return (
          <OverviewPage
            holdings={holdings}
            watchlistCount={watchlist.length}
            totalInvested={totalInvested}
            totalCurrent={totalCurrent}
            totalPnL={totalPnL}
            totalPnLPct={totalPnLPct}
            healthScore={healthScore}
            loadingPrices={loadingPrices}
            onNavigate={setActivePage}
          />
        );

      case "holdings":
        return (
          <HoldingsPage
            holdings={holdings}
            totalInvested={totalInvested}
            totalCurrent={totalCurrent}
            totalPnL={totalPnL}
            loadingPrices={loadingPrices}
            onDelete={deleteHolding}
            onNavigateAdd={() => setActivePage("add")}
            onRefreshPrices={() => fetchLivePrices(holdings)}
          />
        );

      case "add":
        return <AddHoldingPage userId={user.id} onSaved={onHoldingSaved} />;

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
            aiPicks={aiPicks} // ← real ML data (replaces AI_SUGGESTIONS mock)
            loadingAI={loadingAI}
            onAddWatchlist={addWatchlist}
            onRetry={fetchAIPicks}
          />
        );

      case "news":
        return (
          <NewsPage
            holdings={holdings}
            watchlist={watchlist}
            portfolioNews={portfolioNews} // ← real news (replaces PERSONALIZED_NEWS mock)
            loading={loadingNews}
            onRefresh={fetchPortfolioNews}
          />
        );

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
        {/* ── Breadcrumb bar ── */}
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

          {/* Live price loading indicator */}
          {loadingPrices && (
            <span
              style={{
                marginLeft: "auto",
                fontFamily: "var(--mono)",
                fontSize: 9,
                color: "var(--text-muted)",
                letterSpacing: "0.1em",
                display: "flex",
                alignItems: "center",
                gap: 6,
              }}
            >
              <span
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: "50%",
                  background: "var(--green)",
                  display: "inline-block",
                  animation: "pulse 1s infinite",
                }}
              />
              FETCHING LIVE PRICES
            </span>
          )}
        </div>

        {/* ── Main content ── */}
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

        {/* ── Footer ── */}
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
