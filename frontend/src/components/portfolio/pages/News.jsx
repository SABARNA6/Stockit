// frontend/src/pages/portfolio/pages/News.jsx
//
// UPDATED: receives real portfolioNews from GET /api/stocks/<symbol>/news
// (passed down from PortfolioPage — no direct API calls here)

import PageHeader from "../common/PageHeader";

const SENTIMENT_COLOR = {
  Positive: "var(--green)",
  Negative: "#f04060",
  Neutral: "#f0a030",
};

const SENTIMENT_BG = {
  Positive: "var(--green-bg)",
  Negative: "rgba(240,64,96,0.1)",
  Neutral: "rgba(240,160,48,0.1)",
};

export default function NewsPage({
  holdings,
  watchlist,
  portfolioNews, // real data: [{ symbol, news[], sentiment{} }]
  loading,
  onRefresh,
}) {
  const isEmpty = !portfolioNews || portfolioNews.length === 0;
  const allArticles = isEmpty
    ? []
    : portfolioNews.flatMap((p) =>
        (p.news || []).map((n) => ({ ...n, _symbol: p.symbol })),
      );

  return (
    <div>
      <PageHeader
        iconKey="news"
        title="Portfolio News"
        sub={`Latest news for your top holdings · ${allArticles.length} articles`}
        action={
          <button
            onClick={onRefresh}
            style={{
              padding: "8px 16px",
              border: "1px solid var(--border)",
              background: "var(--bg-section)",
              color: "var(--text-muted)",
              borderRadius: 6,
              fontFamily: "var(--mono)",
              fontSize: 10,
              cursor: "pointer",
              letterSpacing: "0.08em",
            }}
          >
            ↻ REFRESH
          </button>
        }
      />

      {/* ── Loading state ── */}
      {loading && (
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
            LOADING NEWS...
          </span>
          <span
            style={{
              fontFamily: "var(--mono)",
              fontSize: 10,
              color: "var(--text-muted)",
            }}
          >
            Fetching latest articles for your holdings
          </span>
        </div>
      )}

      {/* ── Sentiment summary bars ── */}
      {!loading && !isEmpty && (
        <div
          style={{
            display: "flex",
            gap: 12,
            marginBottom: 24,
            flexWrap: "wrap",
          }}
        >
          {portfolioNews.map((p) => {
            const s = p.sentiment || {};
            return (
              <div
                key={p.symbol}
                style={{
                  flex: 1,
                  minWidth: 160,
                  padding: "12px 16px",
                  background: "var(--bg-card)",
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                }}
              >
                <div
                  style={{
                    fontFamily: "var(--mono)",
                    fontSize: 11,
                    fontWeight: 700,
                    color: "var(--text-primary)",
                    marginBottom: 8,
                  }}
                >
                  {p.symbol}
                </div>
                <div style={{ display: "flex", gap: 6 }}>
                  {[
                    { label: "POS", value: s.positive, color: "var(--green)" },
                    { label: "NEU", value: s.neutral, color: "#f0a030" },
                    { label: "NEG", value: s.negative, color: "#f04060" },
                  ].map(({ label, value, color }) => (
                    <div key={label} style={{ textAlign: "center", flex: 1 }}>
                      <div
                        style={{
                          fontFamily: "var(--mono)",
                          fontSize: 13,
                          fontWeight: 700,
                          color,
                        }}
                      >
                        {value != null ? `${value}%` : "—"}
                      </div>
                      <div
                        style={{
                          fontFamily: "var(--mono)",
                          fontSize: 8,
                          color: "var(--text-muted)",
                          letterSpacing: "0.1em",
                        }}
                      >
                        {label}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ── Empty / loading state ── */}
      {!loading && isEmpty && (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            height: "40vh",
            gap: 16,
          }}
        >
          <span style={{ fontSize: 32 }}>📰</span>
          <span
            style={{
              fontFamily: "var(--mono)",
              fontSize: 12,
              color: "var(--text-muted)",
            }}
          >
            No news loaded yet
          </span>
          <button
            onClick={onRefresh}
            style={{
              padding: "8px 20px",
              background: "var(--green)",
              color: "#000",
              border: "none",
              borderRadius: 6,
              fontFamily: "var(--mono)",
              fontSize: 11,
              cursor: "pointer",
              letterSpacing: "0.08em",
            }}
          >
            LOAD NEWS
          </button>
        </div>
      )}

      {/* ── Articles feed (2-column grid) ── */}
      {!loading && !isEmpty && (
        <div className="news-grid">
          {allArticles.map((article, i) => {
            const sentiment = article.sentiment || "Neutral";
            const isHighImpact = (article.tags || []).some((t) =>
              t.includes("high"),
            );

            return (
              <a
                key={i}
                href={article.url || "#"}
                target="_blank"
                rel="noreferrer"
                className="news-card"
                style={{
                  animation: `fadeUp .3s ease both`,
                  animationDelay: `${i * 0.04}s`,
                }}
              >
                <div className="news-tags">
                  <span
                    className="ntag"
                    style={{
                      background: "var(--blue-bg)",
                      color: "var(--blue)",
                      border: "1px solid var(--blue)",
                    }}
                  >
                    {article._symbol}
                  </span>
                  <span
                    className={`ntag ntag-${
                      sentiment === "Positive"
                        ? "pos"
                        : sentiment === "Negative"
                          ? "neg"
                          : "neu"
                    }`}
                  >
                    {sentiment.toUpperCase()}
                  </span>
                  {isHighImpact && (
                    <span className="ntag ntag-hot">High Impact</span>
                  )}
                </div>

                <h4 className="news-title">{article.title}</h4>

                {article.summary && (
                  <p className="news-summary">
                    {article.summary.slice(0, 150)}
                    {article.summary.length > 150 ? "…" : ""}
                  </p>
                )}

                <div className="news-meta mono">
                  <span>{article.source}</span>
                  {article.publishedAt && (
                    <span>
                      {new Date(article.publishedAt).toLocaleDateString(
                        "en-IN",
                        {
                          day: "numeric",
                          month: "short",
                        },
                      )}
                    </span>
                  )}
                  {article.confidence != null && (
                    <span style={{ color: SENTIMENT_COLOR[sentiment] }}>
                      {(article.confidence * 100).toFixed(0)}% confidence
                    </span>
                  )}
                </div>
              </a>
            );
          })}
        </div>
      )}
    </div>
  );
}
