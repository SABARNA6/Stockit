import { useState, useRef } from "react";
import { useStockData } from "./hooks/useStock";
import { useTheme } from "./hooks/useTheme";

import SearchBar from "./components/SearchBar";
import StockHeader from "./components/StockHeader";
import PriceChart from "./components/PriceChart";
import TrendSignals from "./components/TrendSignals";
import RecommendationPanel from "./components/RecommendationPanel";
import FundamentalsGrid from "./components/FundamentalsGrid";
import NewsFeed from "./components/NewsFeed";
import HistoricalTable from "./components/HistoricalTable";
import ThemeToggle from "./components/ThemeToggle";

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

// ─── App ─────────────────────────────────────────────────────────────────────
export default function App() {
  const [symbol, setSymbol] = useState("TCS");
  const {
    overview,
    sparkline,
    trends,
    recommendation,
    loading,
    error,
    reload,
  } = useStockData(symbol);
  const { theme, toggle } = useTheme();

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
        <div className="topbar-right">
          <span className="topbar-timestamp">
            {overview?.lastUpdated
              ? `Updated ${new Date(overview.lastUpdated).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}`
              : "Live · NSE"}
          </span>
          <ThemeToggle theme={theme} onToggle={toggle} />
        </div>
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
          {/* Left: chart + signals */}
          <div className="col-main">
            <SectionTitle>Price Chart</SectionTitle>
            <PriceChart symbol={symbol} theme={theme} />
            <div style={{ marginTop: 20 }}>
              <SectionTitle>Market Signals</SectionTitle>
              <TrendSignals trends={trends} />
            </div>
          </div>

          {/* Right: recommendation */}
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
