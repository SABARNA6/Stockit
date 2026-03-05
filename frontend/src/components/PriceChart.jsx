import { useEffect, useRef, useState, useCallback } from "react";
import { useChart } from "../hooks/useStock";

const TIMEFRAMES = ["1W", "1M", "3M", "6M", "1Y", "ALL"];
const LARGE_TF = ["3M", "6M", "1Y", "ALL"];
const MAX_VISIBLE = 120;
const PAD = { top: 16, right: 20, bottom: 28, left: 60 };

// ─── Helpers ──────────────────────────────────────────────────────────────────
function getColors() {
  const s = getComputedStyle(document.documentElement);
  const g = (v, d) => s.getPropertyValue(v).trim() || d;
  return {
    bg: g("--bg-card", "#1C2230"),
    grid: g("--border", "#2D3344"),
    bull: g("--green", "#22c55e"),
    bear: g("--red", "#ef4444"),
    muted: g("--text-muted", "#6B7280"),
    amber: g("--amber", "#f59e0b"),
    blue: g("--blue", "#3b82f6"),
    text: g("--text-primary", "#ffffff"),
  };
}

function setupCanvas(canvas) {
  const dpr = window.devicePixelRatio || 1;
  const W = canvas.offsetWidth,
    H = canvas.offsetHeight;
  canvas.width = W * dpr;
  canvas.height = H * dpr;
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);
  return { ctx, W, H };
}

function makeScales(candles, W, H) {
  const cw = W - PAD.left - PAD.right;
  const ch = H - PAD.top - PAD.bottom;
  const lo = Math.min(...candles.map((c) => c.low)) * 0.995;
  const hi = Math.max(...candles.map((c) => c.high)) * 1.005;
  const step = cw / candles.length;
  const px = (i) => PAD.left + (i + 0.5) * step;
  const py = (v) => PAD.top + (1 - (v - lo) / (hi - lo)) * ch;
  return { cw, ch, lo, hi, step, px, py };
}

function drawGrid(ctx, W, H, lo, hi, C) {
  const ch = H - PAD.top - PAD.bottom;
  ctx.strokeStyle = C.grid;
  ctx.lineWidth = 0.5;
  for (let i = 0; i <= 5; i++) {
    const y = PAD.top + (ch / 5) * i;
    const v = hi - ((hi - lo) / 5) * i;
    ctx.beginPath();
    ctx.moveTo(PAD.left, y);
    ctx.lineTo(W - PAD.right, y);
    ctx.stroke();
    ctx.fillStyle = C.muted;
    ctx.font = "10px var(--mono, monospace)";
    ctx.textAlign = "right";
    ctx.fillText(
      "₹" + Math.round(v).toLocaleString("en-IN"),
      PAD.left - 6,
      y + 3,
    );
  }
}

function drawCurrentPrice(ctx, W, close, py, C) {
  const cpY = py(close);
  ctx.setLineDash([3, 3]);
  ctx.strokeStyle = C.text;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(PAD.left, cpY);
  ctx.lineTo(W - PAD.right, cpY);
  ctx.stroke();
  ctx.setLineDash([]);
  const label =
    "₹" + close.toLocaleString("en-IN", { maximumFractionDigits: 2 });
  ctx.font = "bold 10px var(--mono, monospace)";
  const lw = ctx.measureText(label).width + 10;
  ctx.fillStyle = C.text;
  ctx.fillRect(W - PAD.right - lw, cpY - 9, lw, 16);
  ctx.fillStyle = C.bg;
  ctx.textAlign = "center";
  ctx.fillText(label, W - PAD.right - lw / 2, cpY + 2);
}

// ─── Draw functions ───────────────────────────────────────────────────────────
export function drawCandles(canvas, candles) {
  if (!canvas || !candles?.length) return;
  const { ctx, W, H } = setupCanvas(canvas);
  const C = getColors();
  const { lo, hi, step, px, py } = makeScales(candles, W, H);

  ctx.fillStyle = C.bg;
  ctx.fillRect(0, 0, W, H);
  drawGrid(ctx, W, H, lo, hi, C);

  const bodyW = Math.max(step * 0.6, 2);
  candles.forEach((c, i) => {
    const bull = c.close >= c.open;
    const col = bull ? C.bull : C.bear;
    const cx = px(i);
    ctx.strokeStyle = col;
    ctx.lineWidth = Math.max(step * 0.08, 1);
    ctx.beginPath();
    ctx.moveTo(cx, py(c.high));
    ctx.lineTo(cx, py(c.low));
    ctx.stroke();
    const bTop = py(Math.max(c.open, c.close));
    const bH = Math.max(Math.abs(py(c.open) - py(c.close)), 1.5);
    ctx.fillStyle = col;
    ctx.fillRect(cx - bodyW / 2, bTop, bodyW, bH);
  });

  drawCurrentPrice(ctx, W, candles[candles.length - 1].close, py, C);
}

export function drawLine(canvas, candles) {
  if (!canvas || !candles?.length) return;
  const { ctx, W, H } = setupCanvas(canvas);
  const C = getColors();
  const { ch, lo, hi, px, py } = makeScales(candles, W, H);

  ctx.fillStyle = C.bg;
  ctx.fillRect(0, 0, W, H);
  drawGrid(ctx, W, H, lo, hi, C);

  const prices = candles.map((c) => c.close);
  const grad = ctx.createLinearGradient(0, PAD.top, 0, PAD.top + ch);
  grad.addColorStop(0, C.bull + "55");
  grad.addColorStop(1, C.bull + "00");

  ctx.beginPath();
  prices.forEach((v, i) =>
    i === 0 ? ctx.moveTo(px(i), py(v)) : ctx.lineTo(px(i), py(v)),
  );
  ctx.lineTo(px(prices.length - 1), PAD.top + ch);
  ctx.lineTo(PAD.left, PAD.top + ch);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();

  ctx.beginPath();
  prices.forEach((v, i) =>
    i === 0 ? ctx.moveTo(px(i), py(v)) : ctx.lineTo(px(i), py(v)),
  );
  ctx.strokeStyle = C.bull;
  ctx.lineWidth = 2;
  ctx.lineJoin = "round";
  ctx.stroke();

  drawCurrentPrice(ctx, W, prices[prices.length - 1], py, C);
}

export function drawVolume(canvas, volumes, avgVolume) {
  if (!canvas || !volumes?.length) return;
  const { ctx, W, H } = setupCanvas(canvas);
  const C = getColors();

  ctx.fillStyle = C.bg;
  ctx.fillRect(0, 0, W, H);

  const cw = W - PAD.left - PAD.right;
  const avg =
    avgVolume || volumes.reduce((a, v) => a + v.volume, 0) / volumes.length;
  const maxV = Math.max(...volumes.map((v) => v.volume));
  const step = cw / volumes.length;
  const bodyW = Math.max(step * 0.6, 2);

  volumes.forEach((v, i) => {
    const bH = (v.volume / maxV) * (H - 4);
    const x = PAD.left + (i + 0.5) * step - bodyW / 2;
    ctx.fillStyle = v.volume > avg * 1.5 ? C.amber : C.blue;
    ctx.globalAlpha = 0.7;
    ctx.fillRect(x, H - bH, bodyW, bH);
  });
  ctx.globalAlpha = 1;
  ctx.fillStyle = C.muted;
  ctx.font = "9px var(--mono, monospace)";
  ctx.textAlign = "right";
  ctx.fillText("VOL", PAD.left - 6, H - 4);
}

// ─── Minimap ──────────────────────────────────────────────────────────────────
function drawMinimap(canvas, allCandles, viewStart, viewEnd) {
  if (!canvas || !allCandles?.length) return;
  const { ctx, W, H } = setupCanvas(canvas);
  const C = getColors();
  const total = allCandles.length;
  const cw = W - PAD.left - PAD.right;

  ctx.fillStyle = C.bg;
  ctx.fillRect(0, 0, W, H);

  const prices = allCandles.map((c) => c.close);
  const lo = Math.min(...prices),
    hi = Math.max(...prices);
  const mpx = (i) => PAD.left + (i / (total - 1)) * cw;
  const mpy = (v) => 4 + (1 - (v - lo) / (hi - lo)) * (H - 8);

  ctx.beginPath();
  prices.forEach((v, i) =>
    i === 0 ? ctx.moveTo(mpx(i), mpy(v)) : ctx.lineTo(mpx(i), mpy(v)),
  );
  ctx.strokeStyle = C.muted;
  ctx.lineWidth = 1;
  ctx.stroke();

  const x1 = mpx(viewStart),
    x2 = mpx(viewEnd);
  ctx.fillStyle = C.bull + "22";
  ctx.fillRect(x1, 0, x2 - x1, H);
  ctx.strokeStyle = C.bull;
  ctx.lineWidth = 1;
  ctx.strokeRect(x1, 0, x2 - x1, H);
}

// ─── Component ────────────────────────────────────────────────────────────────
export default function PriceChart({ symbol, theme }) {
  const [timeframe, setTimeframe] = useState("3M");
  const [chartType, setChartType] = useState("candle");
  const [viewEnd, setViewEnd] = useState(null);
  const { data, loading } = useChart(symbol, timeframe);

  const mainRef = useRef(null);
  const volRef = useRef(null);
  const mapRef = useRef(null);
  const dragging = useRef(false);

  useEffect(() => {
    setChartType(LARGE_TF.includes(timeframe) ? "line" : "candle");
  }, [timeframe]);

  useEffect(() => {
    if (data?.candles?.length) setViewEnd(data.candles.length - 1);
  }, [data]);

  const allCandles = data?.candles ?? [];
  const total = allCandles.length;
  const end = viewEnd ?? total - 1;
  const count = Math.min(MAX_VISIBLE, total);
  const start = Math.max(0, end - count + 1);
  const visibleCandles = allCandles.slice(start, end + 1);
  const visibleVolumes = (data?.volumes ?? []).slice(start, end + 1);

  const redraw = useCallback(() => {
    if (!data || !visibleCandles.length) return;
    const draw = chartType === "line" ? drawLine : drawCandles;
    draw(mainRef.current, visibleCandles);
    drawVolume(volRef.current, visibleVolumes, data.avgVolume);
    if (total > MAX_VISIBLE)
      drawMinimap(mapRef.current, allCandles, start, end);
  }, [data, chartType, start, end, theme]);

  // Regular redraw
  useEffect(() => {
    const id = setTimeout(redraw, 30);
    return () => clearTimeout(id);
  }, [redraw]);

  // Theme change — wait one animation frame so CSS vars are updated first
  useEffect(() => {
    const id = requestAnimationFrame(() => requestAnimationFrame(redraw));
    return () => cancelAnimationFrame(id);
  }, [theme]);

  useEffect(() => {
    const ro = new ResizeObserver(redraw);
    if (mainRef.current) ro.observe(mainRef.current.parentElement);
    return () => ro.disconnect();
  }, [redraw]);

  // Minimap drag-to-pan
  const seekMap = useCallback(
    (e) => {
      if (!mapRef.current || !total) return;
      const rect = mapRef.current.getBoundingClientRect();
      const ratio = Math.max(
        0,
        Math.min(
          1,
          (e.clientX - rect.left - PAD.left) /
            (rect.width - PAD.left - PAD.right),
        ),
      );
      const newEnd = Math.round(ratio * (total - 1));
      setViewEnd(Math.max(count - 1, Math.min(total - 1, newEnd)));
    },
    [total, count],
  );

  const onMapDown = (e) => {
    dragging.current = true;
    seekMap(e);
  };
  const onMapMove = (e) => {
    if (dragging.current) seekMap(e);
  };
  const onMapUp = () => {
    dragging.current = false;
  };

  const onWheel = useCallback(
    (e) => {
      e.preventDefault();
      const delta = Math.sign(e.deltaY);
      setViewEnd((prev) => {
        const cur = prev ?? total - 1;
        return Math.max(count - 1, Math.min(total - 1, cur + delta * 5));
      });
    },
    [total, count],
  );

  useEffect(() => {
    const el = mainRef.current;
    if (!el) return;
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, [onWheel]);

  return (
    <div className="chart-card">
      <div className="chart-toolbar">
        <div className="tf-selector">
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf}
              className={`tf-btn${timeframe === tf ? " active" : ""}`}
              onClick={() => setTimeframe(tf)}
            >
              {tf}
            </button>
          ))}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div className="tf-selector">
            <button
              className={`tf-btn${chartType === "candle" ? " active" : ""}`}
              onClick={() => setChartType("candle")}
            >
              Candle
            </button>
            <button
              className={`tf-btn${chartType === "line" ? " active" : ""}`}
              onClick={() => setChartType("line")}
            >
              Line
            </button>
          </div>
          <span className="chart-badge mono">
            {visibleCandles.length
              ? total > MAX_VISIBLE
                ? `${visibleCandles.length} of ${total} sessions`
                : `${total} sessions`
              : ""}
          </span>
        </div>
      </div>

      <div className="chart-body" style={{ position: "relative" }}>
        {loading && (
          <div className="chart-loading">
            <div className="spinner" />
          </div>
        )}
        <canvas
          ref={mainRef}
          style={{
            width: "100%",
            height: 300,
            display: "block",
            cursor: "crosshair",
          }}
        />
        <canvas
          ref={volRef}
          style={{ width: "100%", height: 64, display: "block", marginTop: 4 }}
        />
      </div>

      {total > MAX_VISIBLE && (
        <canvas
          ref={mapRef}
          style={{
            width: "100%",
            height: 40,
            display: "block",
            marginTop: 4,
            cursor: "ew-resize",
          }}
          onPointerDown={onMapDown}
          onPointerMove={onMapMove}
          onPointerUp={onMapUp}
          onPointerLeave={onMapUp}
        />
      )}
    </div>
  );
}
