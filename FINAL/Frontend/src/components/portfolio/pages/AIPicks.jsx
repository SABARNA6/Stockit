// frontend/src/pages/portfolio/pages/AIPicks.jsx
//
// UPDATED: receives real aiPicks from POST /api/ml/recommend
// (passed down from PortfolioPage — no direct API calls here)

import PageHeader from "../common/PageHeader";

const fmt = {
  pct: (v) =>
    v == null ? "—" : `${v >= 0 ? "+" : ""}${Number(v).toFixed(2)}%`,
  inr: (v) =>
    v == null
      ? "—"
      : `₹${Number(v).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`,
  score: (v) => (v == null ? "—" : Number(v).toFixed(4)),
};

export default function AIPicksPage({
  holdings,
  watchlist,
  aiPicks, // real data from POST /api/ml/recommend
  loadingAI,
  onAddWatchlist,
  onRetry,
}) {
  // ── Loading state ─────────────────────────────────────────────────────────
  if (loadingAI) {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          height: "50vh",
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
          RUNNING ML ANALYSIS...
        </span>
        <span
          style={{
            fontFamily: "var(--mono)",
            fontSize: 10,
            color: "var(--text-muted)",
          }}
        >
          Fetching live data for {holdings.length} portfolio stocks + sector
          peers
        </span>
      </div>
    );
  }

  // ── Error state ───────────────────────────────────────────────────────────
  if (!aiPicks || aiPicks.error) {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          height: "50vh",
          gap: 16,
        }}
      >
        <span style={{ fontSize: 28 }}>🤖</span>
        <span
          style={{
            fontFamily: "var(--mono)",
            fontSize: 12,
            color: "var(--text-muted)",
          }}
        >
          {aiPicks?.error || "AI analysis not loaded yet"}
        </span>
        <button
          onClick={onRetry}
          style={{
            padding: "8px 20px",
            background: "rgba(16, 214, 142, 0.12)",
            color: "var(--green)",
            border: "1px solid rgba(16, 214, 142, 0.4)",
            borderRadius: 6,
            fontFamily: "var(--mono)",
            fontSize: 11,
            fontWeight: 500,
            cursor: "pointer",
            letterSpacing: "0.08em",
            transition: "all .2s ease",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = "rgba(16, 214, 142, 0.2)";
            e.currentTarget.style.borderColor = "rgba(16, 214, 142, 0.6)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "rgba(16, 214, 142, 0.12)";
            e.currentTarget.style.borderColor = "rgba(16, 214, 142, 0.4)";
          }}
        >
          RUN ANALYSIS
        </button>
      </div>
    );
  }

  const recommendations = aiPicks.recommendations || [];
  const backtestSummary = aiPicks.backtest_summary || {};
  const autoSuggested = aiPicks.auto_suggested || [];
  const fetchErrors = aiPicks.fetch_errors || [];

  const watchlistSymbols = new Set(watchlist.map((w) => w.symbol));

  return (
    <div>
      <PageHeader
        iconKey="ai"
        title="AI Stock Picks"
        sub={`ML-powered recommendations based on your portfolio · ${recommendations.length} picks`}
      />

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 10,
          flexWrap: "wrap",
          marginBottom: 14,
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
          Ranked by expected return, volatility, and portfolio concentration
        </span>
        <button
          onClick={onRetry}
          style={{
            padding: "8px 14px",
            border: "1px solid var(--border-light)",
            background: "var(--bg-card)",
            color: "var(--text-muted)",
            borderRadius: 6,
            fontFamily: "var(--mono)",
            fontSize: 10,
            fontWeight: 500,
            cursor: "pointer",
            letterSpacing: "0.08em",
            transition: "all .2s ease",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = "var(--border)";
            e.currentTarget.style.background = "var(--bg-elevated)";
            e.currentTarget.style.color = "var(--text-primary)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = "var(--border-light)";
            e.currentTarget.style.background = "var(--bg-card)";
            e.currentTarget.style.color = "var(--text-muted)";
          }}
        >
          ↻ RE-RUN ANALYSIS
        </button>
      </div>

      {/* ── Sentiment summary bars ── */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
          gap: 12,
          marginBottom: 24,
        }}
      >
        {[
          { label: "RISK PROFILE", value: aiPicks.risk_profile || "Medium" },
          {
            label: "STOCKS SCORED",
            value: aiPicks.tickers_scored || recommendations.length,
          },
          { label: "AUTO-SUGGESTED", value: autoSuggested.length },
          {
            label: "PORTFOLIO VALUE",
            value: aiPicks.portfolio_total
              ? `₹${(aiPicks.portfolio_total / 100000).toFixed(1)}L`
              : "—",
          },
        ].map(({ label, value }) => (
          <div
            key={label}
            style={{
              padding: "12px 14px",
              background: "var(--bg-card)",
              border: "1px solid var(--border-light)",
              borderRadius: 8,
              boxShadow: "inset 0 1px 0 rgba(255,255,255,.02)",
            }}
          >
            <div
              style={{
                fontFamily: "var(--mono)",
                fontSize: 8,
                color: "var(--text-muted)",
                letterSpacing: "0.12em",
                marginBottom: 6,
              }}
            >
              {label}
            </div>
            <div
              style={{
                fontFamily: "var(--mono)",
                fontSize: 16,
                fontWeight: 600,
                color: "var(--text-primary)",
              }}
            >
              {value}
            </div>
          </div>
        ))}
      </div>

      {/* ── Recommendations grid ── */}
      <div className="news-grid">
        {recommendations.map((rec, i) => {
          const bt = backtestSummary[rec.ticker];
          const alreadyHeld = holdings.some((h) => h.symbol === rec.ticker);
          const inWatchlist = watchlistSymbols.has(rec.ticker);
          const predPositive = (rec.predicted_return || 0) > 0;
          const scorePositive = (rec.score || 0) > 0;

          return (
            <div
              key={rec.ticker}
              style={{
                padding: "14px 16px 12px",
                background: "var(--bg-card)",
                border: "1px solid var(--border-light)",
                borderRadius: 8,
                animation: `fadeUp .3s ease both`,
                animationDelay: `${i * 0.04}s`,
                transition: "transform .15s ease, border-color .15s ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = "var(--border)";
                e.currentTarget.style.transform = "translateY(-1px)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "var(--border-light)";
                e.currentTarget.style.transform = "translateY(0)";
              }}
            >
              {/* Header: Rank + Ticker + Status */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  marginBottom: 10,
                }}
              >
                <div
                  style={{
                    width: 28,
                    height: 28,
                    borderRadius: "50%",
                    background: "transparent",
                    border: "1.5px solid rgba(16, 214, 142, 0.5)",
                    color: "var(--green)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontFamily: "var(--mono)",
                    fontSize: 11,
                    fontWeight: 600,
                    flexShrink: 0,
                  }}
                >
                  {rec.rank}
                </div>
                <div style={{ flex: 1 }}>
                  <div
                    style={{
                      fontFamily: "var(--mono)",
                      fontSize: 15,
                      fontWeight: 600,
                      color: "var(--text-primary)",
                    }}
                  >
                    {rec.ticker}
                  </div>
                  <div
                    style={{
                      fontFamily: "var(--mono)",
                      fontSize: 9,
                      color: "var(--text-muted)",
                      letterSpacing: "0.1em",
                    }}
                  >
                    {alreadyHeld ? "IN PORTFOLIO" : "NOT HELD"}
                  </div>
                </div>
                <span
                  className="ntag"
                  style={{
                    background: predPositive
                      ? "rgba(16,214,142,0.15)"
                      : "rgba(240,64,96,0.15)",
                    color: predPositive ? "var(--green)" : "#f04060",
                    border: `1px solid ${predPositive ? "rgba(16,214,142,0.4)" : "rgba(240,64,96,0.4)"}`,
                    flexShrink: 0,
                  }}
                >
                  {fmt.pct(rec.predicted_return * 100)}
                </span>
              </div>

              {/* Tags */}
              <div className="news-tags" style={{ marginBottom: 10 }}>
                <span
                  className="ntag"
                  style={{
                    background: scorePositive
                      ? "rgba(16,214,142,0.15)"
                      : "rgba(240,64,96,0.15)",
                    color: scorePositive ? "var(--green)" : "#f04060",
                    border: `1px solid ${scorePositive ? "rgba(16,214,142,0.4)" : "rgba(240,64,96,0.4)"}`,
                  }}
                >
                  Score {fmt.score(rec.score)}
                </span>
                <span className="ntag ntag-neu">
                  Close {fmt.inr(rec.latest_close)}
                </span>
              </div>

              {/* Metrics */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
                  gap: 10,
                  marginBottom: 10,
                  fontSize: 11,
                }}
              >
                {[
                  {
                    label: "TARGET WEIGHT",
                    value: fmt.pct(rec.target_weight * 100),
                  },
                  {
                    label: "VOLATILITY",
                    value: fmt.pct(rec.volatility_20d * 100),
                  },
                  {
                    label: "EXISTING WEIGHT",
                    value: fmt.pct((rec.existing_weight || 0) * 100),
                  },
                  { label: "MODEL MAE", value: fmt.score(rec.model_mae) },
                ].map(({ label, value }) => (
                  <div key={label}>
                    <span
                      style={{
                        fontFamily: "var(--mono)",
                        fontSize: 8,
                        color: "var(--text-muted)",
                        letterSpacing: "0.1em",
                        display: "block",
                        marginBottom: 2,
                      }}
                    >
                      {label}
                    </span>
                    <span
                      style={{
                        fontFamily: "var(--mono)",
                        fontSize: 12,
                        fontWeight: 500,
                        color: "var(--text-primary)",
                      }}
                    >
                      {value}
                    </span>
                  </div>
                ))}
              </div>

              {/* Backtest summary (if available) */}
              {bt && !bt.error && (
                <div
                  style={{
                    paddingTop: 10,
                    marginTop: 10,
                    borderTop: "1px solid var(--border-light)",
                    fontSize: 10,
                  }}
                >
                  <div
                    style={{
                      fontFamily: "var(--mono)",
                      color: "var(--text-muted)",
                      marginBottom: 6,
                      letterSpacing: "0.08em",
                    }}
                  >
                    60-DAY BACKTEST
                  </div>
                  <div
                    style={{
                      display: "flex",
                      gap: 6,
                      flexWrap: "wrap",
                    }}
                  >
                    {[
                      {
                        label: "HIT",
                        value: `${bt.hit_rate_pct}%`,
                        color:
                          bt.hit_rate_pct >= 55 ? "var(--green)" : "#f0a030",
                      },
                      {
                        label: "RET",
                        value: `${bt.strategy_return_pct > 0 ? "+" : ""}${bt.strategy_return_pct}%`,
                        color:
                          bt.strategy_return_pct > 0
                            ? "var(--green)"
                            : "#f04060",
                      },
                      {
                        label: "ALPHA",
                        value: `${bt.alpha_pct > 0 ? "+" : ""}${bt.alpha_pct}%`,
                        color: bt.alpha_pct > 0 ? "var(--green)" : "#f04060",
                      },
                    ].map(({ label, value, color }) => (
                      <span
                        key={label}
                        style={{ fontFamily: "var(--mono)", color }}
                      >
                        {label} <strong>{value}</strong>
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Watchlist button */}
              {!alreadyHeld && !inWatchlist && (
                <button
                  onClick={() =>
                    onAddWatchlist({
                      symbol: rec.ticker,
                      name: rec.ticker,
                      price: rec.latest_close,
                    })
                  }
                  style={{
                    marginTop: 10,
                    width: "100%",
                    padding: "7px 0",
                    border: "1px solid rgba(16, 214, 142, 0.4)",
                    borderRadius: 5,
                    background: "rgba(16, 214, 142, 0.08)",
                    color: "var(--green)",
                    fontFamily: "var(--mono)",
                    fontSize: 10,
                    fontWeight: 500,
                    cursor: "pointer",
                    letterSpacing: "0.08em",
                    transition: "all .2s ease",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background =
                      "rgba(16, 214, 142, 0.15)";
                    e.currentTarget.style.borderColor =
                      "rgba(16, 214, 142, 0.6)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background =
                      "rgba(16, 214, 142, 0.08)";
                    e.currentTarget.style.borderColor =
                      "rgba(16, 214, 142, 0.4)";
                  }}
                >
                  + WATCHLIST
                </button>
              )}
              {inWatchlist && (
                <div
                  style={{
                    marginTop: 10,
                    padding: "7px 0",
                    textAlign: "center",
                    fontFamily: "var(--mono)",
                    fontSize: 10,
                    color: "var(--text-muted)",
                    letterSpacing: "0.08em",
                  }}
                >
                  ✓ WATCHING
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* ── Fetch errors (non-blocking) ── */}
      {fetchErrors.length > 0 && (
        <div
          style={{
            padding: "12px 16px",
            background: "var(--bg-card)",
            border: "1px solid var(--border-light)",
            borderRadius: 8,
            marginBottom: 16,
          }}
        >
          <div
            style={{
              fontFamily: "var(--mono)",
              fontSize: 9,
              color: "var(--text-muted)",
              marginBottom: 6,
              letterSpacing: "0.08em",
            }}
          >
            COULD NOT FETCH ({fetchErrors.length} tickers):
          </div>
          {fetchErrors.map((e, i) => (
            <div
              key={i}
              style={{
                fontFamily: "var(--mono)",
                fontSize: 9,
                color: "var(--text-muted)",
              }}
            >
              • {e}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
