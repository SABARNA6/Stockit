import { useState } from "react";
import { useNews } from "../hooks/useStock";
import { fmt } from "../api/stockApi";

const FILTERS = ["All", "Positive", "Negative", "Neutral"];

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
      {expanded || !summary ? null : <p className="news-summary">{summary}</p>}
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

export default function NewsFeed({ symbol }) {
  const { data, loading } = useNews(symbol);
  const [filter, setFilter] = useState("All");

  const news = data?.news || [];
  const filtered =
    filter === "All"
      ? news
      : news.filter((n) =>
          n.tags?.some((t) => t.toLowerCase() === filter.toLowerCase()),
        );

  return (
    <div className="news-section">
      {/* Sentiment */}
      <SentimentBar sentiment={data?.sentiment} />

      {/* Filter bar */}
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

      {/* News grid */}
      {loading ? (
        <div className="news-grid">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="news-card">
              <div className="skel skel-short" style={{ marginBottom: 8 }} />
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
    </div>
  );
}
