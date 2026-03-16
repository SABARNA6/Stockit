import { useFundamentals } from "../hooks/useStock";
import { fmt } from "../api/stockApi";

function FundRow({ label, value, color }) {
  return (
    <div className="fund-row">
      <span className="fund-label">{label}</span>
      <span className="fund-value mono" style={color ? { color } : {}}>
        {value ?? "—"}
      </span>
    </div>
  );
}

function FundCard({ title, rows }) {
  return (
    <div className="fund-card">
      <h3 className="fund-card-title">{title}</h3>
      {rows.map((r, i) => <FundRow key={i} {...r} />)}
    </div>
  );
}

export default function FundamentalsGrid({ symbol }) {
  const { data, loading } = useFundamentals(symbol);

  if (loading) return (
    <div className="fund-grid">
      {[0, 1, 2, 3].map(i => (
        <div key={i} className="fund-card">
          <div className="skel skel-wide" style={{ marginBottom: 12 }} />
          {[0, 1, 2, 3].map(j => <div key={j} className="skel skel-med" style={{ marginBottom: 8 }} />)}
        </div>
      ))}
    </div>
  );

  if (!data) return <div className="empty-state">Fundamentals unavailable.</div>;

  // Support both flat and nested response shapes
  const p  = data.profitability    || data;
  const v  = data.valuation        || data;
  const g  = data.growth           || data;
  const fh = data.financialHealth  || data;

  const pct  = val => val != null ? fmt.num(val) + "%" : "—";
  const isGood = (v, threshold, higher = true) =>
    v == null ? undefined : higher ? (v >= threshold ? "var(--green)" : undefined) : (v <= threshold ? "var(--green)" : undefined);

  const cards = [
    {
      title: "Profitability",
      rows: [
        { label: "Net Profit",    value: fmt.crore(p.netProfit),     color: "var(--green)" },
        { label: "EBITDA Margin", value: p.ebitdaMargin != null ? fmt.num(p.ebitdaMargin) + "%" : "—" },
        { label: "ROE",           value: pct(p.roe),                 color: isGood(p.roe, 20) },
        { label: "ROA",           value: pct(p.roa) },
      ],
    },
    {
      title: "Valuation",
      rows: [
        { label: "P/E Ratio",  value: fmt.ratio(v.peRatio) },
        { label: "PEG Ratio",  value: fmt.ratio(v.pegRatio) },
        { label: "P/B Ratio",  value: fmt.ratio(v.pbRatio) },
        { label: "EV/EBITDA",  value: fmt.ratio(v.evEbitda) },
      ],
    },
    {
      title: "Growth",
      rows: [
        { label: "Revenue CAGR (5Y)", value: g.revenueCagr5y != null ? fmt.num(g.revenueCagr5y) + "%" : "—", color: "var(--green)" },
        { label: "Profit CAGR (5Y)",  value: g.profitCagr5y  != null ? fmt.num(g.profitCagr5y)  + "%" : "—" },
        { label: "EPS Growth (TTM)",  value: g.epsGrowthTtm   != null ? fmt.pct(g.epsGrowthTtm * 100) : "—" },
        { label: "Sales Growth",      value: g.salesGrowth    != null ? fmt.pct(g.salesGrowth  * 100) : "—" },
      ],
    },
    {
      title: "Financial Health",
      rows: [
        { label: "Debt / Equity",    value: fh.debtToEquity     != null ? fmt.num(fh.debtToEquity, 2)  : "—", color: isGood(fh.debtToEquity, 1, false) },
        { label: "Interest Coverage",value: fh.interestCoverage != null ? fmt.ratio(fh.interestCoverage) : "—" },
        { label: "Current Ratio",    value: fmt.ratio(fh.currentRatio),   color: isGood(fh.currentRatio, 1.5) },
        { label: "Quick Ratio",      value: fmt.ratio(fh.quickRatio),     color: isGood(fh.quickRatio,  1) },
      ],
    },
  ];

  return (
    <div className="fund-grid">
      {cards.map((c, i) => <FundCard key={i} {...c} />)}
    </div>
  );
}
