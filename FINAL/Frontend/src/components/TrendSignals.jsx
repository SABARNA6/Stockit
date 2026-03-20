import { fmt } from "../api/stockApi";

function SignalCell({ label, value, valueClass, sub, barPct, barColor }) {
  return (
    <div className="signal-cell">
      <div className="signal-label">{label}</div>
      <div className={`signal-value ${valueClass || ""}`}>{value}</div>
      {sub && <div className="signal-sub">{sub}</div>}
      {barPct != null && (
        <div className="signal-bar-track">
          <div className="signal-bar-fill" style={{ width: `${barPct}%`, background: barColor || "var(--amber)" }} />
        </div>
      )}
    </div>
  );
}

export default function TrendSignals({ trends }) {
  if (!trends) return (
    <div className="signals-strip">
      {[0, 1, 2].map(i => <div key={i} className="signal-cell"><div className="skel skel-full" /></div>)}
    </div>
  );

  const { trend, volume, risk } = trends;

  const trendColor = trend?.direction === "bullish" ? "pos" : "neg";
  const volColor   = volume?.status === "Spike" ? "warn" : "";
  const riskColor  = risk?.riskLevel === "High" ? "neg" : risk?.riskLevel === "Low" ? "pos" : "warn";

  return (
    <div className="signals-strip">
      <SignalCell
        label="Trend"
        value={trend?.direction === "bullish" ? "Bullish ▲" : "Bearish ▼"}
        valueClass={trendColor}
        sub={`Strength ${fmt.num(trend?.strength)}%`}
        barPct={trend?.strength}
        barColor={trend?.direction === "bullish" ? "var(--green)" : "var(--red)"}
      />
      <SignalCell
        label="Volume"
        value={volume?.status || "—"}
        valueClass={volColor}
        sub={`Institutional: ${volume?.institutionalActivity || "—"}`}
        barPct={volume?.status === "Spike" ? 85 : volume?.status === "High" ? 65 : 40}
        barColor="var(--amber)"
      />
      <SignalCell
        label="Risk Level"
        value={risk?.riskLevel || "—"}
        valueClass={riskColor}
        sub={`Beta ${fmt.num(risk?.beta, 2)} · ATR ${fmt.price(risk?.atr)}`}
        barPct={risk?.riskLevel === "High" ? 80 : risk?.riskLevel === "Medium" ? 50 : 25}
        barColor={risk?.riskLevel === "High" ? "var(--red)" : "var(--amber)"}
      />
    </div>
  );
}
