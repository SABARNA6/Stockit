import { useState } from "react";
import { useHistorical } from "../hooks/useStock";
import { fmt } from "../api/stockApi";

const PERIODS = [
  { label: "1 Month",  value: "1mo"  },
  { label: "3 Months", value: "3mo"  },
  { label: "6 Months", value: "6mo"  },
  { label: "1 Year",   value: "1y"   },
];

function exportCSV(rows, symbol) {
  const headers = ["Date","Open","High","Low","Close","Volume","Change%"];
  const lines   = [headers.join(",")];
  rows.forEach(r => lines.push([
    r.date, r.open, r.high, r.low, r.close, r.volume, r.changePercent
  ].join(",")));
  const blob = new Blob([lines.join("\n")], { type: "text/csv" });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement("a");
  a.href     = url;
  a.download = `${symbol}_historical.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

export default function HistoricalTable({ symbol }) {
  const [period, setPeriod] = useState("1mo");
  const [page, setPage]     = useState(1);
  const { data, loading }   = useHistorical(symbol, period, page);

  const prices     = data?.prices     || [];
  const pagination = data?.pagination || {};

  const handlePeriodChange = (p) => { setPeriod(p); setPage(1); };

  return (
    <div className="hist-section">
      {/* Controls */}
      <div className="hist-controls">
        <div className="period-selector">
          {PERIODS.map(p => (
            <button
              key={p.value}
              className={`period-btn${period === p.value ? " active" : ""}`}
              onClick={() => handlePeriodChange(p.value)}
            >{p.label}</button>
          ))}
        </div>
        <button
          className="export-btn"
          onClick={() => exportCSV(prices, symbol)}
          disabled={!prices.length}
        >
          ↓ Export CSV
        </button>
      </div>

      {/* Table */}
      <div className="table-wrap">
        <table className="hist-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Open</th>
              <th>High</th>
              <th>Low</th>
              <th>Close</th>
              <th>Volume</th>
              <th>Chg %</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 8 }).map((_, i) => (
                <tr key={i}>
                  {Array.from({ length: 7 }).map((_, j) => (
                    <td key={j}><div className="skel skel-med" /></td>
                  ))}
                </tr>
              ))
            ) : prices.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ textAlign: "center", padding: "24px", color: "var(--text-muted)" }}>
                  No data available.
                </td>
              </tr>
            ) : (
              prices.map((r, i) => (
                <tr key={i} className={r.highVolume ? "row-spike" : ""}>
                  <td className="mono">{r.date}</td>
                  <td className="mono">{fmt.price(r.open)}</td>
                  <td className="mono">{fmt.price(r.high)}</td>
                  <td className="mono">{fmt.price(r.low)}</td>
                  <td className="mono fw">{fmt.price(r.close)}</td>
                  <td className="mono">
                    {fmt.vol(r.volume)}
                    {r.highVolume && <span className="vol-spike-badge">↑</span>}
                  </td>
                  <td className={`mono ${r.changePercent >= 0 ? "pos" : "neg"}`}>
                    {fmt.pct(r.changePercent)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {pagination.totalPages > 1 && (
        <div className="pagination">
          <button
            className="page-btn"
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
          >← Prev</button>

          {Array.from({ length: Math.min(pagination.totalPages, 7) }, (_, i) => {
            const p = i + 1;
            return (
              <button
                key={p}
                className={`page-btn${page === p ? " active" : ""}`}
                onClick={() => setPage(p)}
              >{p}</button>
            );
          })}

          <button
            className="page-btn"
            onClick={() => setPage(p => Math.min(pagination.totalPages, p + 1))}
            disabled={page === pagination.totalPages}
          >Next →</button>
        </div>
      )}
    </div>
  );
}
