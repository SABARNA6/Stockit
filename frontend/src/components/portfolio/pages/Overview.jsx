import PageHeader from "../common/PageHeader";
import StatCard from "../common/StatCard";
import AllocationPie from "../common/AllocationPie";
import HealthRing from "../common/HealthRing";
import { Icon } from "../utils";

export default function OverviewPage({ holdings, watchlistCount, onNavigate }) {
  const totalInvested = holdings.reduce((s, h) => s + h.qty * h.avg_cost, 0);
  const totalCurrent = holdings.reduce((s, h) => s + h.currentValue, 0);
  const totalPnL = totalCurrent - totalInvested;
  const totalRet =
    totalInvested > 0 ? ((totalPnL / totalInvested) * 100).toFixed(2) : 0;
  const health = Math.min(
    100,
    Math.round(
      (holdings.length >= 5 ? 30 : holdings.length * 6) +
        (totalRet > 0
          ? Math.min(40, totalRet * 2)
          : Math.max(0, 40 + parseFloat(totalRet) * 2)) +
        (holdings.length >= 3 ? 30 : holdings.length * 10),
    ),
  );

  // ... (Top Gainer/Loser logic same as original)
  const topGainer = holdings.length
    ? [...holdings].sort(
        (a, b) =>
          b.currentValue -
          b.qty * b.avg_cost -
          (a.currentValue - a.qty * a.avg_cost),
      )[0]
    : null;
  const topLoser = holdings.length
    ? [...holdings].sort(
        (a, b) =>
          a.currentValue -
          a.qty * a.avg_cost -
          (b.currentValue - b.qty * b.avg_cost),
      )[0]
    : null;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 24,
        animation: "fadeUp .35s ease both",
      }}
    >
      <PageHeader
        iconKey="grid"
        title="Portfolio Overview"
        sub={`${holdings.length} holdings · Last refreshed just now`}
      />
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        <StatCard
          label="Invested"
          value={`₹${(totalInvested / 1000).toFixed(1)}K`}
          sub={`${holdings.length} stocks`}
          delay="0s"
        />
        <StatCard
          label="Current Value"
          value={`₹${(totalCurrent / 1000).toFixed(1)}K`}
          color={totalPnL >= 0 ? "var(--green)" : "var(--red)"}
          delay=".05s"
        />
        <StatCard
          label="Total P&L"
          value={`${totalPnL >= 0 ? "+" : ""}₹${(totalPnL / 1000).toFixed(1)}K`}
          sub={`${totalPnL >= 0 ? "▲" : "▼"} ${Math.abs(totalRet)}%`}
          color={totalPnL >= 0 ? "var(--green)" : "var(--red)"}
          delay=".1s"
        />
        <StatCard
          label="Watchlist"
          value={watchlistCount}
          sub="stocks tracked"
          color="var(--amber)"
          delay=".15s"
        />
      </div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 180px",
          gap: 16,
          alignItems: "start",
        }}
      >
        <div
          style={{
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            borderRadius: 12,
            padding: 20,
          }}
        >
          <div
            style={{
              fontSize: 9,
              letterSpacing: "0.18em",
              color: "var(--text-muted)",
              fontFamily: "var(--mono)",
              textTransform: "uppercase",
              marginBottom: 14,
            }}
          >
            Allocation
          </div>
          {holdings.length > 0 ? (
            <AllocationPie holdings={holdings} />
          ) : (
            <div
              style={{
                textAlign: "center",
                color: "var(--text-muted)",
                fontSize: 12,
                padding: "32px 0",
              }}
            >
              No holdings yet
            </div>
          )}
        </div>
        <div
          style={{
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            borderRadius: 12,
            padding: 20,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 8,
          }}
        >
          <div
            style={{
              fontSize: 9,
              letterSpacing: "0.18em",
              color: "var(--text-muted)",
              fontFamily: "var(--mono)",
              textTransform: "uppercase",
            }}
          >
            Portfolio Health
          </div>
          <HealthRing score={health} />
          <p
            style={{
              fontSize: 10,
              color: "var(--text-muted)",
              fontFamily: "var(--mono)",
              textAlign: "center",
              lineHeight: 1.6,
            }}
          >
            {health >= 75
              ? "Well diversified"
              : health >= 50
                ? "Add more variety"
                : "High concentration risk"}
          </p>
        </div>
      </div>
      {/* Quick Actions & Top Movers (Same logic as original, omitted for brevity) */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3,1fr)",
          gap: 10,
        }}
      >
        {/* Map through actions similar to original */}
        <button
          onClick={() => onNavigate("add")}
          style={{
            padding: "16px 18px",
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            borderRadius: 12,
            cursor: "pointer",
            textAlign: "left",
          }}
        >
          <span style={{ color: "var(--green)" }}>{Icon.plus}</span>
          <div
            style={{
              fontSize: 12,
              fontWeight: 600,
              color: "var(--text-primary)",
            }}
          >
            Add Holding
          </div>
        </button>
        {/* ... other buttons */}
      </div>
    </div>
  );
}
