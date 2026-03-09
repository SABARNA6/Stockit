import { useState, useEffect } from "react";
import { useStockData } from "./hooks/useStock";

import SearchBar from "./components/SearchBar";
import StockHeader from "./components/StockHeader";
import PriceChart from "./components/PriceChart";
import TrendSignals from "./components/TrendSignals";
import RecommendationPanel from "./components/RecommendationPanel";
import FundamentalsGrid from "./components/FundamentalsGrid";
import NewsFeed from "./components/NewsFeed";
import HistoricalTable from "./components/HistoricalTable";

// ─── Section ids ──────────────────────────────────────────────────────────────
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

// ─── SectionTitle ─────────────────────────────────────────────────────────────
function SectionTitle({ children }) {
  return <h2 className="section-title">{children}</h2>;
}

// ─── Error Banner ─────────────────────────────────────────────────────────────
function ErrorBanner({ message }) {
  return (
    <div className="error-banner">
      <span>⚠ {message}</span>
    </div>
  );
}

import { Sun, Moon } from "lucide-react";

// ─── Theme Toggle ─────────────────────────────────────────────────────────────
function ThemeToggle({ isLight, onToggle }) {
  return (
    <div
      className="theme-toggle"
      onClick={onToggle}
      title={isLight ? "Switch to dark" : "Switch to light"}
    >
      <Moon size={14} color="var(--text-muted)" />
      <div className={`theme-toggle-track ${isLight ? "active" : ""}`}>
        <div className="theme-toggle-thumb" />
      </div>
      <Sun size={14} color="var(--text-muted)" />
    </div>
  );
}

// ─── App ─────────────────────────────────────────────────────────────────────
export default function App() {
  const [symbol, setSymbol] = useState("TCS");
  const [isLight, setIsLight] = useState(false);

  const {
    overview,
    sparkline,
    trends,
    recommendation,
    loading,
    error,
    reload,
  } = useStockData(symbol);

  // Apply / remove .light class on <html>
  useEffect(() => {
    document.documentElement.classList.toggle("light", isLight);
  }, [isLight]);

  const handleSelect = (sym) => setSymbol(sym.toUpperCase());

  return (
    <div className="app">
      {/* ── Top bar ── */}
      <header className="topbar">
        <div className="topbar-brand">
          <span className="brand-mark">▲</span>
          <span className="brand-name mono">MarketLens</span>
        </div>
        <SearchBar onSelect={handleSelect} />
        <div className="topbar-right mono">
          {overview?.lastUpdated
            ? `Updated ${new Date(overview.lastUpdated).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}`
            : "Live · NSE"}
        </div>
        <ThemeToggle isLight={isLight} onToggle={() => setIsLight((v) => !v)} />
      </header>

      {/* ── Section nav ── */}
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

      {/* ── Error ── */}
      {error && <ErrorBanner message={error} />}

      {/* ── Content ── */}
      <main className="main-content">
        {/* Stock Header */}
        <section id="sec-overview" className="content-section">
          <StockHeader
            overview={overview}
            sparkline={sparkline}
            onWatchlist={() => alert(`${symbol} added to watchlist`)}
          />
        </section>

        {/* Market Overview: Chart + Signals + Recommendation */}
        <section className="content-section two-col-layout">
          <div className="col-main">
            <SectionTitle>Price Chart</SectionTitle>
            <PriceChart symbol={symbol} theme={isLight ? "light" : "dark"} />
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

        {/* Fundamentals */}
        <section id="sec-fundamentals" className="content-section">
          <SectionTitle>Fundamental Analysis</SectionTitle>
          <FundamentalsGrid symbol={symbol} />
        </section>

        {/* News */}
        <section id="sec-news" className="content-section">
          <SectionTitle>News & Sentiment</SectionTitle>
          <NewsFeed symbol={symbol} />
        </section>

        {/* Historical */}
        <section id="sec-historical" className="content-section">
          <SectionTitle>Historical Data</SectionTitle>
          <HistoricalTable symbol={symbol} />
        </section>
      </main>

      {/* ── Footer ── */}
      <footer className="app-footer mono">
        For informational purposes only. Not financial advice. Data via NSE /
        yfinance.
      </footer>
    </div>
  );
}
