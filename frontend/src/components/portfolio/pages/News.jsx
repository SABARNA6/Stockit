import { useState } from "react";
import PageHeader from "../common/PageHeader";
import { Icon, PERSONALIZED_NEWS } from "../utils";

export default function NewsPage({ holdings, watchlist }) {
  const symbols = new Set([
    ...holdings.map((h) => h.symbol),
    ...watchlist.map((w) => w.symbol),
  ]);
  const [filter, setFilter] = useState("all");
  const news = PERSONALIZED_NEWS.filter(
    (n) => symbols.size === 0 || symbols.has(n.symbol),
  );
  const filtered =
    filter === "all" ? news : news.filter((n) => n.sentiment === filter);

  const sentMap = {
    positive: "var(--green)",
    negative: "var(--red)",
    neutral: "var(--amber)",
  };
  const sentBgMap = {
    positive: "var(--green-bg)",
    negative: "var(--red-bg)",
    neutral: "var(--amber-bg)",
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 20,
        animation: "fadeUp .35s ease both",
      }}
    >
      <PageHeader
        iconKey="news"
        title="Personalised News"
        sub={`Latest news for your ${symbols.size} tracked stocks`}
      />

      {/* Filter */}
      <div
        style={{
          display: "flex",
          gap: 4,
          background: "var(--bg-elevated)",
          padding: 3,
          borderRadius: 8,
          width: "fit-content",
          border: "1px solid var(--border)",
        }}
      >
        {[
          ["all", "All"],
          ["positive", "Positive"],
          ["negative", "Negative"],
          ["neutral", "Neutral"],
        ].map(([v, l]) => (
          <button
            key={v}
            onClick={() => setFilter(v)}
            style={{
              padding: "6px 14px",
              background: filter === v ? "var(--bg-card)" : "transparent",
              border: "none",
              borderRadius: 6,
              color: filter === v ? "var(--text-primary)" : "var(--text-muted)",
              fontFamily: "var(--mono)",
              fontSize: 11,
              cursor: "pointer",
              letterSpacing: "0.08em",
              transition: "all .15s",
            }}
          >
            {l}
          </button>
        ))}
      </div>

      {symbols.size === 0 && (
        <div
          style={{
            padding: "14px 18px",
            background: "var(--amber-bg)",
            border: "1px solid var(--amber)",
            borderRadius: 10,
            fontSize: 12,
            color: "var(--amber)",
            fontFamily: "var(--mono)",
          }}
        >
          ⚡ Add holdings or a watchlist to see personalised news.
        </div>
      )}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill,minmax(320px,1fr))",
          gap: 14,
        }}
      >
        {filtered.map((n, i) => (
          <div
            key={n.id}
            style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              borderRadius: 12,
              padding: 20,
              display: "flex",
              flexDirection: "column",
              gap: 10,
              cursor: "pointer",
              animation: `fadeUp .4s ease both`,
              animationDelay: `${i * 0.05}s`,
              transition: "border-color .15s, transform .15s",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "var(--border-light)";
              e.currentTarget.style.transform = "translateY(-2px)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "var(--border)";
              e.currentTarget.style.transform = "none";
            }}
          >
            <div
              style={{
                display: "flex",
                gap: 6,
                alignItems: "center",
                flexWrap: "wrap",
              }}
            >
              <span
                style={{
                  fontSize: 9,
                  padding: "2px 9px",
                  borderRadius: 20,
                  fontFamily: "var(--mono)",
                  fontWeight: 700,
                  letterSpacing: "0.1em",
                  background: sentBgMap[n.sentiment],
                  color: sentMap[n.sentiment],
                  border: `1px solid ${sentMap[n.sentiment]}`,
                }}
              >
                {n.sentiment.toUpperCase()}
              </span>
              <span
                style={{
                  fontSize: 9,
                  padding: "2px 9px",
                  borderRadius: 20,
                  fontFamily: "var(--mono)",
                  background: "var(--blue-bg)",
                  color: "var(--blue)",
                  border: "1px solid var(--blue)",
                }}
              >
                {n.symbol}
              </span>
            </div>

            <h3
              style={{
                fontFamily: "var(--serif)",
                fontSize: 14,
                fontWeight: 600,
                color: "var(--text-primary)",
                lineHeight: 1.45,
                margin: 0,
              }}
            >
              {n.title}
            </h3>

            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                fontSize: 10,
                color: "var(--text-muted)",
                fontFamily: "var(--mono)",
              }}
            >
              <span>{n.source}</span>
              <span>{n.time}</span>
            </div>

            <p
              style={{
                fontSize: 12,
                color: "var(--text-secondary)",
                lineHeight: 1.6,
                margin: 0,
              }}
            >
              {n.summary}
            </p>
          </div>
        ))}

        {filtered.length === 0 && (
          <div
            style={{
              gridColumn: "1/-1",
              textAlign: "center",
              padding: "40px 20px",
              color: "var(--text-muted)",
              fontSize: 13,
              border: "1px dashed var(--border)",
              borderRadius: 12,
            }}
          >
            No {filter} news found for your holdings.
          </div>
        )}
      </div>
    </div>
  );
}
