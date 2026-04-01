import { useState, useEffect, useRef } from "react";
import { useNews } from "../hooks/useStock";
import { fmt } from "../api/stockApi";

const API = window.STOCK_API_BASE || "/api";
const FILTERS = ["All", "Positive", "Negative", "Neutral"];

// ─────────────────────────────────────────────────────────────────────────────
// EQUITY INTELLIGENCE FETCH
// Response shape: { analysis: { overall_direction, sentiment_score,
//   price_impact, results[], articles_analyzed, articles_input }, ... }
// ─────────────────────────────────────────────────────────────────────────────
async function fetchEI(symbol, signal) {
  const res = await fetch(`${API}/equity/analyze/${symbol}?hours_back=24`, { signal });
  if (!res.ok) throw new Error(res.status);
  const json = await res.json();
  return json.analysis ?? json.data ?? json;
}

// ─────────────────────────────────────────────────────────────────────────────
// CONSTANTS
// ─────────────────────────────────────────────────────────────────────────────
const DIR_COLOR = {
  BULLISH: "#10d68e",
  BEARISH: "#f04060",
  NEUTRAL: "#f0a030",
};
const DIR_BG = {
  BULLISH: "rgba(16,214,142,0.09)",
  BEARISH: "rgba(240,64,96,0.09)",
  NEUTRAL: "rgba(240,160,48,0.09)",
};
const CONF_COLOR = { HIGH: "#10d68e", MEDIUM: "#f0a030", LOW: "#888780" };
const TYPE_LABEL = {
  INDIRECT_MACRO: "Macro",
  DIRECT_COMPANY: "Company",
  SECTOR: "Sector",
  NOISE: "Noise",
};

// ─────────────────────────────────────────────────────────────────────────────
// EXISTING SUB-COMPONENTS (unchanged)
// ─────────────────────────────────────────────────────────────────────────────
function SentimentBar({ sentiment }) {
  if (!sentiment) return null;
  const { positive = 0, neutral = 0, negative = 0 } = sentiment;
  return (
    <div className="sentiment-section">
      <div className="sentiment-bar">
        <div
          className="sb-pos"
          style={{ flex: positive }}
          title={`Positive ${positive}%`}
        />
        <div
          className="sb-neu"
          style={{ flex: neutral }}
          title={`Neutral ${neutral}%`}
        />
        <div
          className="sb-neg"
          style={{ flex: negative }}
          title={`Negative ${negative}%`}
        />
      </div>
      <div className="sentiment-legend">
        <span className="sleg-item">
          <span className="sleg-dot pos" />
          {positive.toFixed(0)}% Positive
        </span>
        <span className="sleg-item">
          <span className="sleg-dot neu" />
          {neutral.toFixed(0)}% Neutral
        </span>
        <span className="sleg-item">
          <span className="sleg-dot neg" />
          {negative.toFixed(0)}% Negative
        </span>
      </div>
    </div>
  );
}

function NewsCard({ article }) {
  const [expanded, setExpanded] = useState(false);
  const { title, summary, source, publishedAt, url, tags = [] } = article;
  const sentiment =
    tags.find((t) => ["positive", "negative", "neutral"].includes(t)) ||
    "neutral";
  const highImpact = tags.includes("high-impact") || article.highImpact;
  const sentClass =
    sentiment === "positive" ? "pos" : sentiment === "negative" ? "neg" : "neu";

  return (
    <div className="news-card" onClick={() => setExpanded((e) => !e)}>
      <div className="news-tags">
        <span className={`ntag ntag-${sentClass}`}>{sentiment}</span>
        {highImpact && <span className="ntag ntag-hot">High Impact</span>}
      </div>
      <h4 className="news-title">{title}</h4>
      <div className="news-meta mono">
        <span>{source}</span>
        <span>{fmt.date(publishedAt)}</span>
      </div>
      {!expanded && summary && <p className="news-summary">{summary}</p>}
      {expanded && summary && (
        <>
          <p className="news-summary">{summary}</p>
          {url && (
            <a
              className="news-link"
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
            >
              Read full article →
            </a>
          )}
        </>
      )}
      <div className="news-expand mono">
        {expanded ? "▲ Collapse" : "▼ Expand"}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// EQUITY INTELLIGENCE PANEL
// ─────────────────────────────────────────────────────────────────────────────
function EIPanel({ symbol }) {
  const [data, setData] = useState(null);
  const [dataSymbol, setDataSymbol] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [open, setOpen] = useState(false);
  const [showAll, setShowAll] = useState(false);
  const abortRef = useRef(null);

  useEffect(() => {
    setData(null);
    setDataSymbol(null);
    setError(null);
    setOpen(false);
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
  }, [symbol]);

  const toggle = async () => {
    if (data) {
      setOpen((o) => !o);
      return;
    }
    if (loading) return;
    setOpen(true);
    setLoading(true);
    setError(null);
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const analysisData = await fetchEI(symbol, controller.signal);
      setData(analysisData);
      setDataSymbol(symbol);
    } catch (e) {
      if (e.name === "AbortError") return;
      setError(
        e.message === "503"
          ? "Equity Intelligence offline — start equity_intelligence_v3/server.py"
          : `Analysis failed: ${e.message}`,
      );
    } finally {
      setLoading(false);
      abortRef.current = null;
    }
  };

  // Derived values from real response shape
  // Only use data if it's for the current symbol
  const isValidData = data && dataSymbol === symbol;
  const direction = isValidData
    ? data?.overall_direction || "NEUTRAL"
    : "NEUTRAL";
  const score = isValidData ? data?.sentiment_score : null;
  const impact = isValidData ? data?.price_impact || {} : {};
  const results = isValidData ? data?.results || [] : [];
  const analyzed = isValidData
    ? (data?.articles_analyzed ?? results.length)
    : 0;
  const input = isValidData ? data?.articles_input : null;
  const cached = isValidData ? data?.cache_status === "hit" : false;
  const visible = showAll ? results : results.slice(0, 4);

  return (
    <div
      style={{
        border: "1px solid var(--border)",
        borderRadius: 10,
        marginBottom: 20,
        overflow: "hidden",
      }}
    >
      {/* ── Trigger row ── */}
      <button
        onClick={toggle}
        style={{
          width: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "13px 18px",
          background: "var(--bg-card)",
          border: "none",
          cursor: "pointer",
          borderBottom: open ? "1px solid var(--border)" : "none",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {/* Status dot */}
          <div
            style={{
              width: 7,
              height: 7,
              borderRadius: "50%",
              flexShrink: 0,
              background: data
                ? DIR_COLOR[direction]
                : loading
                  ? "#f0a030"
                  : "var(--text-muted)",
            }}
          />
          <span
            style={{
              fontFamily: "var(--mono)",
              fontSize: 11,
              fontWeight: 700,
              color: "var(--text-primary)",
              letterSpacing: "0.1em",
            }}
          >
            LLM EQUITY INTELLIGENCE
          </span>
          {/* Direction badge — shown once loaded */}
          {isValidData && (
            <span
              style={{
                padding: "2px 10px",
                borderRadius: 4,
                fontFamily: "var(--mono)",
                fontSize: 10,
                fontWeight: 700,
                letterSpacing: "0.08em",
                background: DIR_BG[direction],
                color: DIR_COLOR[direction],
              }}
            >
              {direction}
            </span>
          )}
          {/* Score pill */}
          {isValidData && score != null && (
            <span
              style={{
                padding: "2px 8px",
                borderRadius: 4,
                fontFamily: "var(--mono)",
                fontSize: 10,
                background: "var(--bg-section)",
                color: "var(--text-muted)",
              }}
            >
              Score:{" "}
              <span
                style={{
                  color:
                    score >= 6 ? "#10d68e" : score >= 4 ? "#f0a030" : "#f04060",
                  fontWeight: 700,
                }}
              >
                {score.toFixed(1)}/10
              </span>
            </span>
          )}
          {/* Cache badge */}
          {cached && (
            <span
              style={{
                fontFamily: "var(--mono)",
                fontSize: 9,
                color: "var(--text-muted)",
                padding: "1px 6px",
                border: "1px solid var(--border)",
                borderRadius: 3,
              }}
            >
              CACHED
            </span>
          )}
          {/* Idle hint */}
          {!data && !loading && !error && (
            <span
              style={{
                fontFamily: "var(--mono)",
                fontSize: 10,
                color: "var(--text-muted)",
              }}
            >
              Click to run deep LLM analysis
            </span>
          )}
          {loading && (
            <span
              style={{
                fontFamily: "var(--mono)",
                fontSize: 10,
                color: "#f0a030",
              }}
            >
              Analysing {input ? `${input} articles` : "news"} with LLM…
            </span>
          )}
        </div>
        <span
          style={{
            fontFamily: "var(--mono)",
            fontSize: 12,
            color: "var(--text-muted)",
          }}
        >
          {loading ? "⏳" : open ? "▲" : "▼"}
        </span>
      </button>

      {/* ── Body ── */}
      {open && !loading && (
        <div
          style={{
            padding: "16px 18px",
            background: "var(--bg-section)",
            display: "flex",
            flexDirection: "column",
            gap: 16,
          }}
        >
          {error && (
            <div
              style={{
                fontFamily: "var(--mono)",
                fontSize: 11,
                color: "#f04060",
                padding: "10px 14px",
                background: "rgba(240,64,96,0.08)",
                border: "1px solid rgba(240,64,96,0.2)",
                borderRadius: 8,
              }}
            >
              ⚠ {error}
            </div>
          )}

          {isValidData && (
            <>
              {/* ── Summary metric cards ── */}
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                {/* Direction */}
                <div
                  style={{
                    flex: 1,
                    minWidth: 110,
                    padding: "10px 14px",
                    borderRadius: 8,
                    textAlign: "center",
                    background: DIR_BG[direction],
                    border: `1px solid ${DIR_COLOR[direction]}`,
                  }}
                >
                  <div
                    style={{
                      fontFamily: "var(--mono)",
                      fontSize: 8,
                      letterSpacing: "0.14em",
                      color: DIR_COLOR[direction],
                      marginBottom: 4,
                    }}
                  >
                    DIRECTION
                  </div>
                  <div
                    style={{
                      fontFamily: "var(--mono)",
                      fontSize: 17,
                      fontWeight: 700,
                      color: DIR_COLOR[direction],
                    }}
                  >
                    {direction}
                  </div>
                </div>

                {/* Sentiment score */}
                {score != null && (
                  <div
                    style={{
                      flex: 1,
                      minWidth: 110,
                      padding: "10px 14px",
                      borderRadius: 8,
                      textAlign: "center",
                      background: "var(--bg-card)",
                      border: "1px solid var(--border)",
                    }}
                  >
                    <div
                      style={{
                        fontFamily: "var(--mono)",
                        fontSize: 8,
                        letterSpacing: "0.14em",
                        color: "var(--text-muted)",
                        marginBottom: 4,
                      }}
                    >
                      SENTIMENT SCORE
                    </div>
                    <div
                      style={{
                        fontFamily: "var(--mono)",
                        fontSize: 17,
                        fontWeight: 700,
                        color:
                          score >= 6
                            ? "#10d68e"
                            : score >= 4
                              ? "#f0a030"
                              : "#f04060",
                      }}
                    >
                      {score.toFixed(1)}
                      <span
                        style={{
                          fontSize: 10,
                          color: "var(--text-muted)",
                          fontWeight: 400,
                        }}
                      >
                        /10
                      </span>
                    </div>
                  </div>
                )}

                {/* Expected move */}
                {impact.overall_move_range && (
                  <div
                    style={{
                      flex: 1,
                      minWidth: 130,
                      padding: "10px 14px",
                      borderRadius: 8,
                      textAlign: "center",
                      background: "var(--bg-card)",
                      border: "1px solid var(--border)",
                    }}
                  >
                    <div
                      style={{
                        fontFamily: "var(--mono)",
                        fontSize: 8,
                        letterSpacing: "0.14em",
                        color: "var(--text-muted)",
                        marginBottom: 4,
                      }}
                    >
                      EXPECTED MOVE
                    </div>
                    <div
                      style={{
                        fontFamily: "var(--mono)",
                        fontSize: 13,
                        fontWeight: 700,
                        color:
                          impact.overall_direction === "BULLISH"
                            ? "#10d68e"
                            : impact.overall_direction === "BEARISH"
                              ? "#f04060"
                              : "#f0a030",
                      }}
                    >
                      {impact.overall_move_range}
                    </div>
                    <div
                      style={{
                        fontFamily: "var(--mono)",
                        fontSize: 9,
                        color: "var(--text-muted)",
                        marginTop: 2,
                      }}
                    >
                      {impact.overall_direction}
                    </div>
                  </div>
                )}

                {/* Signal counts */}
                {impact.signals && (
                  <div
                    style={{
                      flex: 1,
                      minWidth: 130,
                      padding: "10px 14px",
                      borderRadius: 8,
                      background: "var(--bg-card)",
                      border: "1px solid var(--border)",
                    }}
                  >
                    <div
                      style={{
                        fontFamily: "var(--mono)",
                        fontSize: 8,
                        letterSpacing: "0.14em",
                        color: "var(--text-muted)",
                        marginBottom: 8,
                      }}
                    >
                      ARTICLE SIGNALS
                    </div>
                    <div style={{ display: "flex", gap: 14 }}>
                      {[
                        {
                          label: "Bull",
                          v: impact.signals.bullish,
                          c: "#10d68e",
                        },
                        {
                          label: "Neu",
                          v: impact.signals.neutral,
                          c: "#f0a030",
                        },
                        {
                          label: "Bear",
                          v: impact.signals.bearish,
                          c: "#f04060",
                        },
                      ].map(({ label, v, c }) => (
                        <div key={label} style={{ textAlign: "center" }}>
                          <div
                            style={{
                              fontFamily: "var(--mono)",
                              fontSize: 16,
                              fontWeight: 700,
                              color: c,
                            }}
                          >
                            {v}
                          </div>
                          <div
                            style={{
                              fontFamily: "var(--mono)",
                              fontSize: 8,
                              color: "var(--text-muted)",
                            }}
                          >
                            {label}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Articles count */}
                <div
                  style={{
                    flex: 1,
                    minWidth: 100,
                    padding: "10px 14px",
                    borderRadius: 8,
                    textAlign: "center",
                    background: "var(--bg-card)",
                    border: "1px solid var(--border)",
                  }}
                >
                  <div
                    style={{
                      fontFamily: "var(--mono)",
                      fontSize: 8,
                      letterSpacing: "0.14em",
                      color: "var(--text-muted)",
                      marginBottom: 4,
                    }}
                  >
                    ANALYSED
                  </div>
                  <div
                    style={{
                      fontFamily: "var(--mono)",
                      fontSize: 17,
                      fontWeight: 700,
                      color: "var(--text-primary)",
                    }}
                  >
                    {analyzed}
                  </div>
                  {input && (
                    <div
                      style={{
                        fontFamily: "var(--mono)",
                        fontSize: 8,
                        color: "var(--text-muted)",
                        marginTop: 2,
                      }}
                    >
                      of {input} ingested
                    </div>
                  )}
                </div>
              </div>

              {/* ── Per-article LLM results (2-column grid) ── */}
              {results.length > 0 && (
                <div>
                  <div
                    style={{
                      fontFamily: "var(--mono)",
                      fontSize: 9,
                      color: "var(--text-muted)",
                      letterSpacing: "0.14em",
                      marginBottom: 12,
                    }}
                  >
                    ARTICLE BREAKDOWN
                  </div>
                  <div className="news-grid" style={{ marginBottom: 12 }}>
                    {visible.map((item, i) => {
                      const dir = (item.direction || "NEUTRAL").toUpperCase();
                      const conf = (item.confidence || "LOW").toUpperCase();
                      const type = TYPE_LABEL[item.type] || item.type || "";
                      const sentClass =
                        dir === "BULLISH"
                          ? "pos"
                          : dir === "BEARISH"
                            ? "neg"
                            : "neu";

                      return (
                        <div
                          key={item.hash || i}
                          className="ei-news-card"
                          style={{
                            padding: "12px 14px",
                            borderRadius: 8,
                            background: "var(--bg-card)",
                            border: "1px solid var(--border)",
                            cursor: "pointer",
                            transition: "all .2s",
                            display: "flex",
                            flexDirection: "column",
                            gap: 8,
                          }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.borderColor =
                              DIR_COLOR[dir] || "var(--border)";
                            e.currentTarget.style.background =
                              "var(--bg-elevated)";
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.borderColor = "var(--border)";
                            e.currentTarget.style.background = "var(--bg-card)";
                          }}
                        >
                          {/* Tags row */}
                          <div className="news-tags">
                            <span className={`ntag ntag-${sentClass}`}>
                              {dir}
                            </span>
                            {conf !== "LOW" && (
                              <span
                                className="ntag"
                                style={{
                                  background: `${CONF_COLOR[conf]}20`,
                                  color: CONF_COLOR[conf],
                                  border: `1px solid ${CONF_COLOR[conf]}`,
                                }}
                              >
                                {conf}
                              </span>
                            )}
                            {type && (
                              <span className="ntag" style={{ fontSize: 9 }}>
                                {type}
                              </span>
                            )}
                          </div>

                          {/* Title */}
                          {item.title && (
                            <h4 className="news-title">
                              {item.link ? (
                                <a
                                  href={item.link}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  onClick={(e) => e.stopPropagation()}
                                  style={{
                                    color: "inherit",
                                    textDecoration: "none",
                                  }}
                                >
                                  {item.title}
                                </a>
                              ) : (
                                item.title
                              )}
                            </h4>
                          )}

                          {/* Cause / Summary */}
                          {item.cause && (
                            <p
                              className="news-summary"
                              style={{
                                fontFamily: "var(--mono)",
                                fontSize: 10,
                                lineHeight: 1.5,
                                marginBottom: 0,
                              }}
                            >
                              {item.cause}
                            </p>
                          )}

                          {/* Metadata row */}
                          <div className="news-meta mono">
                            {item.source && <span>{item.source}</span>}
                            {item.predicted_move_range && (
                              <span
                                style={{
                                  color: DIR_COLOR[dir] || "var(--text-muted)",
                                  fontWeight: 700,
                                }}
                              >
                                {item.predicted_move_range}
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Show more button */}
                  {results.length > 4 && (
                    <button
                      onClick={() => setShowAll((s) => !s)}
                      style={{
                        width: "100%",
                        padding: "8px",
                        background: "transparent",
                        border: "1px dashed var(--border)",
                        borderRadius: 6,
                        fontFamily: "var(--mono)",
                        fontSize: 10,
                        color: "var(--text-muted)",
                        cursor: "pointer",
                        letterSpacing: "0.08em",
                      }}
                    >
                      {showAll
                        ? "▲ Show less"
                        : `▼ Show ${results.length - 4} more articles`}
                    </button>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN EXPORT  (with tabs for Sentiment & News vs LLM Intelligence)
// ─────────────────────────────────────────────────────────────────────────────
export default function NewsFeed({ symbol }) {
  const { data, loading } = useNews(symbol);
  const [filter, setFilter] = useState("All");
  const [activeTab, setActiveTab] = useState("sentiment"); // "sentiment" | "llm"

  const news = data?.news || [];
  const filtered =
    filter === "All"
      ? news
      : news.filter((n) =>
          n.tags?.some((t) => t.toLowerCase() === filter.toLowerCase()),
        );

  const tabs = [
    { id: "sentiment", label: "Sentiment & News" },
    { id: "llm", label: "LLM Intelligence" },
  ];

  return (
    <div className="news-section">
      {/* ── Tab navigation ── */}
      <div
        style={{
          display: "flex",
          gap: 2,
          borderBottom: "1px solid var(--border)",
          marginBottom: 20,
        }}
      >
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: "10px 16px",
              background:
                activeTab === tab.id ? "var(--bg-card)" : "transparent",
              border: "none",
              borderBottom:
                activeTab === tab.id
                  ? "2px solid var(--text-primary)"
                  : "2px solid transparent",
              color:
                activeTab === tab.id
                  ? "var(--text-primary)"
                  : "var(--text-muted)",
              fontFamily: "var(--mono)",
              fontSize: 10,
              fontWeight: 700,
              cursor: "pointer",
              letterSpacing: "0.08em",
              transition: "all .2s",
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── Sentiment & News Tab ── */}
      {activeTab === "sentiment" && (
        <>
          {/* ── FinBERT sentiment bar ── */}
          <SentimentBar sentiment={data?.sentiment} />

          {/* ── Filter bar ── */}
          <div className="news-filter-bar">
            {FILTERS.map((f) => (
              <button
                key={f}
                className={`nfilt-btn${filter === f ? " active" : ""}`}
                onClick={() => setFilter(f)}
              >
                {f}
              </button>
            ))}
          </div>

          {/* ── News grid ── */}
          {loading ? (
            <div className="news-grid">
              {[0, 1, 2, 3].map((i) => (
                <div key={i} className="news-card">
                  <div
                    className="skel skel-short"
                    style={{ marginBottom: 8 }}
                  />
                  <div className="skel skel-wide" style={{ marginBottom: 6 }} />
                  <div className="skel skel-med" style={{ marginBottom: 6 }} />
                  <div className="skel skel-wide" />
                </div>
              ))}
            </div>
          ) : !filtered.length ? (
            <div className="empty-state">
              No {filter !== "All" ? filter.toLowerCase() : ""} news found.
            </div>
          ) : (
            <div className="news-grid">
              {filtered.map((article, i) => (
                <NewsCard key={i} article={article} />
              ))}
            </div>
          )}
        </>
      )}

      {/* ── LLM Intelligence Tab ── */}
      {activeTab === "llm" && <EIPanel symbol={symbol} />}
    </div>
  );
}
