import PageHeader from "../common/PageHeader";
import { Icon, getAISignal } from "../utils";

export default function HoldingsPage({ holdings, onDelete, onNavigateAdd }) {
  const totalInvested = holdings.reduce((s, h) => s + h.qty * h.avg_cost, 0);
  const totalCurrent = holdings.reduce((s, h) => s + h.currentValue, 0);
  const totalPnL = totalCurrent - totalInvested;

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
        iconKey="chart"
        title="My Holdings"
        sub={`${holdings.length} stocks · P&L ${totalPnL >= 0 ? "+" : ""}₹${(totalPnL / 1000).toFixed(1)}K`}
        action={
          <button
            onClick={onNavigateAdd}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "8px 16px",
              background: "var(--green)",
              border: "none",
              borderRadius: 8,
              color: "#fff",
              fontFamily: "var(--mono)",
              fontSize: 11,
              cursor: "pointer",
            }}
          >
            {Icon.plus} Add Holding
          </button>
        }
      />
      {holdings.length === 0 ? (
        <div
          style={{
            textAlign: "center",
            padding: "60px 20px",
            border: "1px dashed var(--border)",
            borderRadius: 12,
            color: "var(--text-muted)",
            fontSize: 13,
          }}
        >
          <div style={{ fontSize: 32, marginBottom: 12 }}>📊</div>
          No holdings yet.{" "}
          <span
            style={{ color: "var(--green)", cursor: "pointer" }}
            onClick={onNavigateAdd}
          >
            Add your first stock →
          </span>
        </div>
      ) : (
        <div
          style={{
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            borderRadius: 12,
            overflow: "hidden",
          }}
        >
          <div style={{ overflowX: "auto" }}>
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                minWidth: 700,
              }}
            >
              <thead>
                <tr style={{ background: "var(--bg-elevated)" }}>
                  {[
                    "Symbol",
                    "Qty",
                    "Avg Cost",
                    "LTP",
                    "Invested",
                    "Current",
                    "P&L",
                    "Return",
                    "Signal",
                    "",
                  ].map((h) => (
                    <th
                      key={h}
                      style={{
                        padding: "10px 14px",
                        textAlign: "left",
                        fontFamily: "var(--mono)",
                        fontSize: 9,
                        fontWeight: 600,
                        letterSpacing: "0.15em",
                        textTransform: "uppercase",
                        color: "var(--text-muted)",
                        whiteSpace: "nowrap",
                        borderBottom: "1px solid var(--border)",
                      }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {holdings.map((h) => {
                  const invested = h.qty * h.avg_cost;
                  const pnl = h.currentValue - invested;
                  const ret = ((pnl / invested) * 100).toFixed(2);
                  const sig = getAISignal(h.symbol, h.avg_cost, h.ltp);
                  const pos = pnl >= 0;
                  return (
                    <tr
                      key={h.id}
                      style={{
                        borderBottom: "1px solid var(--border)",
                        transition: "background .12s",
                      }}
                      onMouseEnter={(e) =>
                        (e.currentTarget.style.background = "var(--bg-hover)")
                      }
                      onMouseLeave={(e) =>
                        (e.currentTarget.style.background = "transparent")
                      }
                    >
                      <td style={{ padding: "12px 14px" }}>
                        <span
                          style={{
                            fontFamily: "var(--mono)",
                            fontSize: 13,
                            fontWeight: 700,
                            color: "var(--blue)",
                          }}
                        >
                          {h.symbol}
                        </span>
                      </td>
                      <td
                        style={{
                          padding: "12px 14px",
                          fontFamily: "var(--mono)",
                          fontSize: 12,
                          color: "var(--text-secondary)",
                        }}
                      >
                        {h.qty}
                      </td>
                      <td
                        style={{
                          padding: "12px 14px",
                          fontFamily: "var(--mono)",
                          fontSize: 12,
                          color: "var(--text-secondary)",
                        }}
                      >
                        ₹{h.avg_cost.toLocaleString("en-IN")}
                      </td>
                      <td
                        style={{
                          padding: "12px 14px",
                          fontFamily: "var(--mono)",
                          fontSize: 12,
                          color: pos ? "var(--green)" : "var(--red)",
                        }}
                      >
                        ₹
                        {h.ltp.toLocaleString("en-IN", {
                          maximumFractionDigits: 0,
                        })}
                      </td>
                      <td
                        style={{
                          padding: "12px 14px",
                          fontFamily: "var(--mono)",
                          fontSize: 12,
                          color: "var(--text-secondary)",
                        }}
                      >
                        ₹{(invested / 1000).toFixed(1)}K
                      </td>
                      <td
                        style={{
                          padding: "12px 14px",
                          fontFamily: "var(--mono)",
                          fontSize: 12,
                          color: "var(--text-secondary)",
                        }}
                      >
                        ₹{(h.currentValue / 1000).toFixed(1)}K
                      </td>
                      <td
                        style={{
                          padding: "12px 14px",
                          fontFamily: "var(--mono)",
                          fontSize: 12,
                          color: pos ? "var(--green)" : "var(--red)",
                        }}
                      >
                        {pos ? "+" : ""}₹{(pnl / 1000).toFixed(1)}K
                      </td>
                      <td
                        style={{
                          padding: "12px 14px",
                          fontFamily: "var(--mono)",
                          fontSize: 12,
                          color: pos ? "var(--green)" : "var(--red)",
                        }}
                      >
                        {pos ? "▲" : "▼"}
                        {Math.abs(ret)}%
                      </td>
                      <td style={{ padding: "12px 14px" }}>
                        <span
                          title={sig.r}
                          style={{
                            padding: "3px 9px",
                            borderRadius: 20,
                            fontSize: 9,
                            fontFamily: "var(--mono)",
                            fontWeight: 700,
                            letterSpacing: "0.1em",
                            background: sig.bg,
                            color: sig.c,
                            border: `1px solid ${sig.c}`,
                          }}
                        >
                          {sig.v}
                        </span>
                      </td>
                      <td style={{ padding: "12px 14px" }}>
                        <button
                          onClick={() => onDelete(h.id)}
                          style={{
                            background: "transparent",
                            border: "none",
                            color: "var(--text-muted)",
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                          }}
                          title="Remove holding"
                          onMouseEnter={(e) =>
                            (e.currentTarget.style.color = "var(--red)")
                          }
                          onMouseLeave={(e) =>
                            (e.currentTarget.style.color = "var(--text-muted)")
                          }
                        >
                          {Icon.trash}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
