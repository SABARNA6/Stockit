import { useState, useEffect, useCallback } from "react";
import { supabase } from "../supabaseClient";
import { useAuth } from "../context/AuthContext";

// Import Sub-components
import Sidebar from "./portfolio/common/Sidebar";
import OverviewPage from "./portfolio/pages/Overview";
import HoldingsPage from "./portfolio/pages/Holdings";
import AddHoldingPage from "./portfolio/pages/AddHolding";
import WatchlistPage from "./portfolio/pages/Watchlist";
import AIPicksPage from "./portfolio/pages/AIPicks";
import NewsPage from "./portfolio/pages/News";
import { mockLTP, NAV_ITEMS } from "./portfolio/utils";

export default function PortfolioPage({ onBack }) {
  const { user, displayName, avatarInitial } = useAuth();
  const [activePage, setActivePage] = useState("overview");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [holdings, setHoldings] = useState([]);
  const [watchlist, setWatchlist] = useState([]);
  const [loadingData, setLoadingData] = useState(true);

  // ── Fetch Data ────────────────────────────────────────────────────────
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

  // ── Mutations ────────────────────────────────────────────────────────
  const deleteHolding = async (id) => {
    await supabase.from("portfolio").delete().eq("id", id);
    setHoldings((h) => h.filter((x) => x.id !== id));
  };

  const addWatchlist = async (stock) => {
    const { data } = await supabase
      .from("watchlist")
      .insert({
        user_id: user.id,
        symbol: stock.symbol,
        name: stock.name || "",
        sector: stock.sector || "",
        price: stock.price || null,
        target_price: stock.target_price || null, // ← new
        note: stock.note || null, // ← new
      })
      .select()
      .single();
    if (data) setWatchlist((w) => [data, ...w]);
  };

  const removeWatchlist = async (id) => {
    await supabase.from("watchlist").delete().eq("id", id);
    setWatchlist((w) => w.filter((x) => x.id !== id));
  };

  // ── Render ────────────────────────────────────────────────────────
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
