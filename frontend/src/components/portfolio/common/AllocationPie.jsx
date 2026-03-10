import { PIE_COLORS } from "../utils";

export default function AllocationPie({ holdings }) {
  const total = holdings.reduce((s, h) => s + h.currentValue, 0);
  if (!total) return null;
  let cum = -Math.PI / 2;
  const cx = 90,
    cy = 90,
    r = 70,
    ir = 42;
  const slices = holdings.map((h, i) => {
    const pct = h.currentValue / total;
    const s = cum;
    cum += pct * 2 * Math.PI;
    const e = cum;
    const large = pct > 0.5 ? 1 : 0;
    const p = (a, rad) => [cx + rad * Math.cos(a), cy + rad * Math.sin(a)];
    const [x1, y1] = p(s, r),
      [x2, y2] = p(e, r),
      [ix1, iy1] = p(s, ir),
      [ix2, iy2] = p(e, ir);
    return {
      d: `M${x1},${y1}A${r},${r},0,${large},1,${x2},${y2}L${ix2},${iy2}A${ir},${ir},0,${large},0,${ix1},${iy1}Z`,
      pct,
      color: PIE_COLORS[i % PIE_COLORS.length],
      symbol: h.symbol,
    };
  });
  return (
    <div
      style={{
        display: "flex",
        gap: 20,
        alignItems: "center",
        flexWrap: "wrap",
      }}
    >
      <svg width={180} height={180} style={{ flexShrink: 0 }}>
        {slices.map((s, i) => (
          <path
            key={i}
            d={s.d}
            fill={s.color}
            opacity={0.9}
            stroke="var(--bg-card)"
            strokeWidth={2}
          >
            <title>
              {s.symbol}: {(s.pct * 100).toFixed(1)}%
            </title>
          </path>
        ))}
        <text
          x={cx}
          y={cy - 6}
          textAnchor="middle"
          fill="var(--text-primary)"
          fontSize={13}
          fontFamily="var(--mono)"
          fontWeight={700}
        >
          ₹{(total / 100000).toFixed(1)}L
        </text>
        <text
          x={cx}
          y={cx + 10}
          textAnchor="middle"
          fill="var(--text-muted)"
          fontSize={8}
          fontFamily="var(--mono)"
          letterSpacing={1}
        >
          TOTAL
        </text>
      </svg>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 6,
          flex: 1,
          minWidth: 130,
        }}
      >
        {holdings.map((h, i) => (
          <div
            key={h.symbol}
            style={{ display: "flex", alignItems: "center", gap: 7 }}
          >
            <div
              style={{
                width: 9,
                height: 9,
                borderRadius: 2,
                background: PIE_COLORS[i % PIE_COLORS.length],
                flexShrink: 0,
              }}
            />
            <span
              style={{
                fontSize: 11,
                color: "var(--text-secondary)",
                flex: 1,
                fontFamily: "var(--mono)",
              }}
            >
              {h.symbol}
            </span>
            <span
              style={{
                fontSize: 10,
                color: "var(--text-muted)",
                fontFamily: "var(--mono)",
              }}
            >
              {((h.currentValue / total) * 100).toFixed(1)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
