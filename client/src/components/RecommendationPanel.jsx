import { useState } from "react";
import { fmt } from "../api/stockApi";

const TABS = ["technical", "fundamental", "sentiment", "risks"];
const TAB_LABELS = { technical: "Technical", fundamental: "Fund.", sentiment: "Sentiment", risks: "Risks" };

// ─── Entry price visual ladder ────────────────────────────────────────────────
function EntryLadder({ plan, currentPrice }) {
  if (!plan) return null;
  const { accumulationZone, stopLoss, breakoutAbove } = plan;
  const lo  = stopLoss * 0.98;
  const hi  = breakoutAbove * 1.02;
  const rng = hi - lo;
  const pct = v => `${Math.min(Math.max(((v - lo) / rng) * 100, 0), 100).toFixed(1)}%`;

  const markers = [
    { x: pct(stopLoss),              label: "STOP", val: fmt.price(stopLoss),            color: "var(--red)"   },
    { x: pct(accumulationZone?.min), label: "ZONE", val: fmt.price(accumulationZone?.min), color: "var(--green)" },
    { x: pct(currentPrice),          label: "NOW",  val: fmt.price(currentPrice),          color: "var(--text-primary)" },
    { x: pct(breakoutAbove),         label: "BRK",  val: fmt.price(breakoutAbove),          color: "var(--amber)" },
  ];

  return (
    <div className="entry-ladder">
      {/* Zone fill */}
      <div className="ladder-track">
        <div className="ladder-zone" style={{
          left: pct(accumulationZone?.min),
          width: `${((accumulationZone?.max - accumulationZone?.min) / rng) * 100}%`,
        }} />
        {markers.map((m, i) => (
          <div key={i} className="ladder-marker" style={{ left: m.x }}>
            <div className="lm-line" style={{ background: m.color }} />
            <div className="lm-label" style={{ color: m.color }}>{m.label}</div>
            <div className="lm-val mono">{m.val}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Reasoning bullet list ────────────────────────────────────────────────────
function ReasonList({ items = [], type = "neutral" }) {
  if (!items.length) return <p className="muted" style={{ fontSize: 12, padding: "8px 0" }}>No data available.</p>;
  const bullet = type === "pos" ? "▲" : type === "neg" ? "▼" : "◆";
  const cls    = type === "pos" ? "pos" : type === "neg" ? "neg" : "warn";
  return (
    <ul className="reason-list">
      {items.map((item, i) => (
        <li key={i}>
          <span className={`reason-bullet ${cls}`}>{bullet}</span>
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

// ─── RecommendationPanel ──────────────────────────────────────────────────────
export default function RecommendationPanel({ recommendation, currentPrice }) {
  const [activeTab, setActiveTab] = useState("technical");

  if (!recommendation) return (
    <div className="rec-panel">
      <div className="skel skel-wide" style={{ height: 80 }} />
      <div className="skel skel-med" style={{ marginTop: 12 }} />
    </div>
  );

  const { recommendation: verdict, confidence, timeHorizon,
          technicalScore, fundamentalScore, entryPlan, reasoning } = recommendation;

  const verdictClass = verdict === "buy" ? "pos" : verdict === "sell" ? "neg" : "warn";
  const tabType      = { technical: "neg", fundamental: "pos", sentiment: "warn", risks: "neg" };

  return (
    <div className="rec-panel">
      {/* Verdict */}
      <div className="rec-header-row">
        <div className={`verdict-badge ${verdictClass}`}>
          {(verdict || "hold").toUpperCase()}
        </div>
        <div className="rec-meta">
          <span className="mono" style={{ fontSize: 11 }}>{timeHorizon}</span>
        </div>
      </div>

      {/* Confidence bar */}
      <div className="conf-section">
        <div className="conf-label-row">
          <span>Confidence</span>
          <span className="mono">{confidence}%</span>
        </div>
        <div className="conf-track">
          <div className="conf-fill" style={{ width: `${confidence}%` }} />
        </div>
      </div>

      {/* Scores */}
      <div className="score-rows">
        <div className="score-row">
          <span>Technical Score</span>
          <span className="mono neg">{technicalScore} / 100</span>
        </div>
        <div className="score-row">
          <span>Fundamental Score</span>
          <span className="mono pos">{fundamentalScore} / 100</span>
        </div>
      </div>

      {/* Entry Ladder */}
      <div className="section-divider" />
      <div className="entry-section-label mono">Entry Plan</div>
      <EntryLadder plan={entryPlan} currentPrice={currentPrice} />

      <div className="entry-rows">
        <div className="entry-row">
          <span>Accumulation Zone</span>
          <span className="mono pos">{fmt.price(entryPlan?.accumulationZone?.min)} – {fmt.price(entryPlan?.accumulationZone?.max)}</span>
        </div>
        <div className="entry-row">
          <span>Breakout Above</span>
          <span className="mono">{fmt.price(entryPlan?.breakoutAbove)}</span>
        </div>
        <div className="entry-row">
          <span>Stop Loss</span>
          <span className="mono neg">Below {fmt.price(entryPlan?.stopLoss)}</span>
        </div>
        <div className="entry-row">
          <span>Risk : Reward</span>
          <span className="rr-badge mono">1 : {fmt.num(entryPlan?.riskRewardRatio, 1)}</span>
        </div>
        <div className="entry-row">
          <span>Position Size</span>
          <span className="mono">{entryPlan?.positionSize}% of Portfolio</span>
        </div>
      </div>

      {/* Reasoning tabs */}
      <div className="section-divider" />
      <div className="reason-tabs">
        {TABS.map(t => (
          <button
            key={t}
            className={`rtab-btn${activeTab === t ? " active" : ""}`}
            onClick={() => setActiveTab(t)}
          >{TAB_LABELS[t]}</button>
        ))}
      </div>

      <ReasonList items={reasoning?.[activeTab] || []} type={tabType[activeTab]} />
    </div>
  );
}
