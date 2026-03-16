import { useState, useEffect } from "react";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { useStockData } from "./hooks/useStock";

import AuthPage from "./AuthPage";
import UserMenu from "./components/UserMenu";
import SearchBar from "./components/SearchBar";
import StockHeader from "./components/StockHeader";
import PriceChart from "./components/PriceChart";
import TrendSignals from "./components/TrendSignals";
import RecommendationPanel from "./components/RecommendationPanel";
import FundamentalsGrid from "./components/FundamentalsGrid";
import NewsFeed from "./components/NewsFeed";
import HistoricalTable from "./components/HistoricalTable";
import PortfolioPage from "./components/PortfolioPage1";

import { Sun, Moon, BarChart2, Briefcase } from "lucide-react";

const SECTIONS = [
  { id: "overview", label: "Overview" },
  { id: "strategy", label: "Strategy" },
  { id: "fundamentals", label: "Fundamentals" },
  { id: "news", label: "News" },
  { id: "historical", label: "Historical" },
];

function scrollToSection(id) {
  document
    .getElementById(`sec-${id}`)
    ?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function SectionTitle({ children }) {
  return <h2 className="section-title">{children}</h2>;
}

function ErrorBanner({ message }) {
  return (
    <div className="error-banner">
      <span>⚠ {message}</span>
    </div>
  );
}

function ThemeToggle({ isLight, onToggle }) {
  return (
    <div className="theme-toggle" onClick={onToggle}>
      <Moon size={14} color="var(--text-muted)" />
      <div className={`theme-toggle-track ${isLight ? "active" : ""}`}>
        <div className="theme-toggle-thumb" />
      </div>
      <Sun size={14} color="var(--text-muted)" />
    </div>
  );
}

function LoadingSplash() {
  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--bg-primary)",
        gap: 16,
      }}
    >
      <span style={{ fontSize: 32, color: "var(--green)" }}>▲</span>
      <div className="spinner" />
      <span
        style={{
          fontFamily: "var(--mono)",
          fontSize: 11,
          color: "var(--text-muted)",
          letterSpacing: "0.15em",
        }}
      >
        LOADING...
      </span>
    </div>
  );
}

// ─── Inner App ────────────────────────────────────────────────────────────────
function AppInner() {
  const { user, loading } = useAuth();
  const [symbol, setSymbol] = useState("TCS");
  const [isLight, setIsLight] = useState(true); // ← light by default
  const [page, setPage] = useState("market"); // "market" | "portfolio" | "auth"

  const {
    overview,
    sparkline,
    trends,
    recommendation,
    error,
    loading: stockLoading,
  } = useStockData(symbol);

  useEffect(() => {
    document.documentElement.classList.toggle("light", isLight);
  }, [isLight]);
  useEffect(() => {
    if (user && page === "auth") {
      setPage("market");
    }
  }, [user]);

  if (window.location.pathname === "/auth/callback") {
    return <AuthCallback />;
  }
  if (loading) return <LoadingSplash />;

  if (page === "auth") return <AuthPage onBack={() => setPage("market")} />;

  if (page === "portfolio")
    return <PortfolioPage onBack={() => setPage("market")} />;

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-brand">
          <span className="brand-mark">▲</span>
          <span className="brand-name mono">MarketLens</span>
        </div>

        <SearchBar onSelect={(sym) => setSymbol(sym.toUpperCase())} />

        {/* Page switcher */}
        <div style={{ display: "flex", gap: 4 }}>
          {[
            {
              id: "market",
              label: "Market",
              icon: <BarChart2 size={13} />,
              color: "var(--blue)",
              bg: "var(--blue-bg)",
            },
            {
              id: "portfolio",
              label: "Portfolio",
              icon: <Briefcase size={13} />,
              color: "var(--green)",
              bg: "var(--green-bg)",
            },
          ].map((p) => (
            <button
              key={p.id}
              onClick={() => {
                if (p.id === "portfolio" && !user) {
                  setPage("auth"); // nudge to sign in
                  return;
                }
                setPage(p.id);
              }}
              title={
                p.id === "portfolio" && !user
                  ? "Sign in to access your Portfolio"
                  : ""
              }
              style={{
                display: "flex",
                alignItems: "center",
                gap: 5,
                padding: "6px 12px",
                background: page === p.id ? p.bg : "transparent",
                border: `1px solid ${page === p.id ? p.color : "var(--border)"}`,
                borderRadius: "var(--r-sm)",
                color:
                  page === p.id
                    ? p.color
                    : p.id === "portfolio" && !user
                      ? "var(--text-muted)"
                      : "var(--text-muted)",
                fontFamily: "var(--mono)",
                fontSize: 11,
                cursor: "pointer",
                letterSpacing: "0.08em",
                transition: "all .15s",
                opacity: p.id === "portfolio" && !user ? 0.5 : 1, // dimmed when locked
              }}
            >
              {p.icon} {p.label}
              {p.id === "portfolio" && !user && (
                <span style={{ fontSize: 10 }}>🔒</span>
              )}
            </button>
          ))}
        </div>

        <div className="topbar-right mono">
          {overview?.lastUpdated
            ? `Updated ${new Date(overview.lastUpdated).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}`
            : "Live · NSE"}
        </div>

        <ThemeToggle isLight={isLight} onToggle={() => setIsLight((v) => !v)} />

        {/* ── Auth: show UserMenu if logged in, Sign In button if not ── */}
        {user ? (
          <UserMenu onNavigatePortfolio={() => setPage("portfolio")} />
        ) : (
          <button
            onClick={() => setPage("auth")}
            style={{
              padding: "6px 14px",
              background: "var(--green-bg)",
              border: "1px solid var(--green)",
              borderRadius: "var(--r-sm)",
              color: "var(--green)",
              fontFamily: "var(--mono)",
              fontSize: 11,
              cursor: "pointer",
              letterSpacing: "0.08em",
              transition: "all .15s",
              flexShrink: 0,
            }}
          >
            Sign In
          </button>
        )}
      </header>

      <nav className="section-nav">
        {SECTIONS.map((s) => (
          <button
            key={s.id}
            className="snav-btn"
            onClick={() => scrollToSection(s.id)}
          >
            {s.label}
          </button>
        ))}
      </nav>

      {error && <ErrorBanner message={error} />}

      <main className="main-content">
        <section id="sec-overview" className="content-section">
          {stockLoading ? (
            <div className="header-skeleton">
              <div className="skel skel-wide" />
              <div className="skel skel-med" />
              <div className="skel skel-wide" />
            </div>
          ) : (
            <StockHeader
              overview={overview}
              sparkline={sparkline}
              onWatchlist={() => setPage("auth")}
            />
          )}
        </section>

        <section className="content-section two-col-layout">
          <div className="col-main">
            <SectionTitle>Price Chart</SectionTitle>
            {/* Only mount PriceChart after overview is loaded */}
            {stockLoading || !overview?.lastUpdated ? (
              <div
                style={{
                  padding: "40px 20px",
                  textAlign: "center",
                  color: "var(--text-muted)",
                }}
              >
                Loading chart data...
              </div>
            ) : (
              <PriceChart symbol={symbol} theme={isLight ? "light" : "dark"} />
            )}
            <div style={{ marginTop: 20 }}>
              <SectionTitle>Market Signals</SectionTitle>
              <TrendSignals trends={trends} />
            </div>
          </div>
          <div className="col-side" id="sec-strategy">
            <SectionTitle>Strategy</SectionTitle>
            <RecommendationPanel
              recommendation={recommendation}
              currentPrice={overview?.currentPrice}
            />
          </div>
        </section>

        {/* Only render these sections after overview loads successfully */}
        {!stockLoading && overview?.lastUpdated && (
          <>
            <section id="sec-fundamentals" className="content-section">
              <SectionTitle>Fundamental Analysis</SectionTitle>
              <FundamentalsGrid symbol={symbol} />
            </section>

            <section id="sec-news" className="content-section">
              <SectionTitle>News & Sentiment</SectionTitle>
              <NewsFeed symbol={symbol} />
            </section>

            <section id="sec-historical" className="content-section">
              <SectionTitle>Historical Data</SectionTitle>
              <HistoricalTable symbol={symbol} />
            </section>
          </>
        )}
      </main>

      <footer className="app-footer mono">
        For informational purposes only. Not financial advice. Data via NSE /
        yfinance.
      </footer>
    </div>
  );
}

// ─── Root ─────────────────────────────────────────────────────────────────────
export default function App() {
  return (
    <AuthProvider>
      <AppInner />
    </AuthProvider>
  );
}
