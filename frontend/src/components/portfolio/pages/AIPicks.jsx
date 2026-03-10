import { useState } from "react";
import PageHeader from "../common/PageHeader";
import { Icon, AI_SUGGESTIONS } from "../utils";

export default function AIPicksPage({ holdings, watchlist, onAddWatchlist }) {
  const [budget, setBudget] = useState(50000);
  const holdingSymbols = new Set(holdings.map((h) => h.symbol));
  const watchlistSymbols = new Set(watchlist.map((w) => w.symbol));
  const suggestions = AI_SUGGESTIONS.filter(
    (s) => !holdingSymbols.has(s.symbol),
  );

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
        iconKey="sparkle"
        title="AI Investment Picks"
        sub="Personalised suggestions based on your portfolio composition"
        action={
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span
              style={{
                fontSize: 11,
                color: "var(--text-muted)",
                fontFamily: "var(--mono)",
              }}
            >
              Budget:
            </span>
            <input
              type="number"
              value={budget}
              onChange={(e) => setBudget(Number(e.target.value))}
              style={{
                background: "var(--bg-elevated)",
                border: "1px solid var(--border)",
                borderRadius: 6,
                color: "var(--text-primary)",
                fontFamily: "var(--mono)",
                fontSize: 12,
                padding: "6px 10px",
                width: 110,
                outline: "none",
              }}
            />
          </div>
        }
      />

      {/* Why these picks */}
      <div
        style={{
          padding: "14px 18px",
          background: "var(--purple-bg,var(--blue-bg))",
          border: "1px solid var(--purple,var(--blue))",
          borderRadius: 10,
          fontSize: 12,
          color: "var(--text-secondary)",
          lineHeight: 1.7,
        }}
      >
        <span style={{ color: "var(--purple,var(--blue))", fontWeight: 700 }}>
          How we pick:{" "}
        </span>
        Based on your current holdings, we identify gaps in sector
        diversification, P/E balance, and market-cap spread. Stocks you already
        hold are excluded.
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill,minmax(280px,1fr))",
          gap: 16,
        }}
      >
        {suggestions.map((s, i) => {
          const canBuy = budget >= s.price;
          const qty = Math.floor(budget / s.price);
          const inWish = watchlistSymbols.has(s.symbol);
          return (
            <div
              key={s.symbol}
              style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
                borderRadius: 12,
                padding: 20,
                display: "flex",
                flexDirection: "column",
                gap: 12,
                animation: `fadeUp .4s ease both`,
                animationDelay: `${i * 0.06}s`,
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
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                }}
              >
                <div>
                  <div
                    style={{
                      fontFamily: "var(--mono)",
                      fontSize: 15,
                      fontWeight: 700,
                      color: "var(--text-primary)",
                    }}
                  >
                    {s.symbol}
                  </div>
                  <div
                    style={{
                      fontSize: 11,
                      color: "var(--text-secondary)",
                      marginTop: 2,
                    }}
                  >
                    {s.name}
                  </div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div
                    style={{
                      fontFamily: "var(--mono)",
                      fontSize: 14,
                      fontWeight: 600,
                      color: "var(--text-primary)",
                    }}
                  >
                    ₹{s.price.toLocaleString("en-IN")}
                  </div>
                  <span
                    style={{
                      fontSize: 9,
                      padding: "2px 8px",
                      borderRadius: 20,
                      background: "var(--blue-bg)",
                      color: "var(--blue)",
                      fontFamily: "var(--mono)",
                    }}
                  >
                    {s.sector}
                  </span>
                </div>
              </div>

              {/* Score bar */}
              <div>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    fontSize: 10,
                    color: "var(--text-muted)",
                    marginBottom: 5,
                  }}
                >
                  <span style={{ fontFamily: "var(--mono)" }}>
                    AI Match Score
                  </span>
                  <span
                    style={{
                      color: "#8b5cf6",
                      fontFamily: "var(--mono)",
                      fontWeight: 700,
                    }}
                  >
                    {s.score}/100
                  </span>
                </div>
                <div
                  style={{
                    height: 4,
                    background: "var(--border)",
                    borderRadius: 2,
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      height: "100%",
                      width: `${s.score}%`,
                      background: "linear-gradient(90deg,#8b5cf6,#a78bfa)",
                      borderRadius: 2,
                      transition: "width 1.2s cubic-bezier(.4,0,.2,1)",
                    }}
                  />
                </div>
              </div>

              <p
                style={{
                  fontSize: 11,
                  color: "var(--text-secondary)",
                  lineHeight: 1.7,
                  margin: 0,
                }}
              >
                {s.reason}
              </p>

              <div
                style={{
                  fontSize: 10,
                  fontFamily: "var(--mono)",
                  color: canBuy ? "var(--green)" : "var(--amber)",
                }}
              >
                {canBuy
                  ? `✓ Buy ${qty} share${qty !== 1 ? "s" : ""} within ₹${budget.toLocaleString(
                      "en-IN",
                    )} budget`
                  : `⚠ Above your ₹${budget.toLocaleString("en-IN")} budget`}
              </div>

              <button
                onClick={() => !inWish && onAddWatchlist(s)}
                style={{
                  padding: "8px 0",
                  background: inWish ? "var(--bg-elevated)" : "var(--amber-bg)",
                  border: `1px solid ${
                    inWish ? "var(--border)" : "var(--amber)"
                  }`,
                  borderRadius: 8,
                  color: inWish ? "var(--text-muted)" : "var(--amber)",
                  fontFamily: "var(--mono)",
                  fontSize: 10,
                  cursor: inWish ? "default" : "pointer",
                  letterSpacing: "0.08em",
                  transition: "all .15s",
                }}
              >
                {inWish ? "★ In Watchlist" : "☆ Add to Watchlist"}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
