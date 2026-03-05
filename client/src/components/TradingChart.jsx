import { useEffect, useRef, useState, useCallback } from "react";

const INTERVALS = ["1m", "5m", "15m", "1h", "4h", "1D", "1W"];

const INDICATORS = {
  SMA: { label: "SMA", color: "#f59e0b" },
  EMA: { label: "EMA", color: "#34d399" },
  BOLL: { label: "Bollinger", color: "#818cf8" },
  RSI: { label: "RSI", color: "#f472b6" },
  MACD: { label: "MACD", color: "#60a5fa" },
  VOL: { label: "Volume", color: "#6b7280" },
};

function generateOHLC(count = 200, basePrice = 42000) {
  const data = [];
  let time = Math.floor(Date.now() / 1000) - count * 60 * 60;
  let close = basePrice;
  let volume = 1000;
  for (let i = 0; i < count; i++) {
    const change = (Math.random() - 0.49) * close * 0.02;
    const open = close;
    close = Math.max(100, open + change);
    const high = Math.max(open, close) * (1 + Math.random() * 0.008);
    const low = Math.min(open, close) * (1 - Math.random() * 0.008);
    volume = Math.max(100, volume + (Math.random() - 0.5) * 500);
    data.push({
      time,
      open: parseFloat(open.toFixed(2)),
      high: parseFloat(high.toFixed(2)),
      low: parseFloat(low.toFixed(2)),
      close: parseFloat(close.toFixed(2)),
      volume: parseFloat(volume.toFixed(2)),
    });
    time += 3600;
  }
  return data;
}

function calcSMA(data, period = 20) {
  return data.map((d, i) => {
    if (i < period - 1) return null;
    const sum = data.slice(i - period + 1, i + 1).reduce((a, b) => a + b.close, 0);
    return { time: d.time, value: parseFloat((sum / period).toFixed(2)) };
  }).filter(Boolean);
}

function calcEMA(data, period = 20) {
  const k = 2 / (period + 1);
  let ema = data[0].close;
  return data.map((d, i) => {
    if (i === 0) return { time: d.time, value: parseFloat(ema.toFixed(2)) };
    ema = d.close * k + ema * (1 - k);
    return { time: d.time, value: parseFloat(ema.toFixed(2)) };
  });
}

function calcBollinger(data, period = 20) {
  return data.map((d, i) => {
    if (i < period - 1) return null;
    const slice = data.slice(i - period + 1, i + 1).map(x => x.close);
    const mean = slice.reduce((a, b) => a + b) / period;
    const std = Math.sqrt(slice.reduce((a, b) => a + (b - mean) ** 2, 0) / period);
    return {
      time: d.time,
      upper: parseFloat((mean + 2 * std).toFixed(2)),
      middle: parseFloat(mean.toFixed(2)),
      lower: parseFloat((mean - 2 * std).toFixed(2)),
    };
  }).filter(Boolean);
}

function calcRSI(data, period = 14) {
  const result = [];
  for (let i = period; i < data.length; i++) {
    const gains = [], losses = [];
    for (let j = i - period + 1; j <= i; j++) {
      const diff = data[j].close - data[j - 1].close;
      if (diff > 0) gains.push(diff); else losses.push(Math.abs(diff));
    }
    const avgGain = gains.reduce((a, b) => a + b, 0) / period;
    const avgLoss = losses.reduce((a, b) => a + b, 0) / period;
    const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
    result.push({ time: data[i].time, value: parseFloat((100 - 100 / (1 + rs)).toFixed(2)) });
  }
  return result;
}

function calcMACD(data) {
  const ema12 = calcEMA(data, 12);
  const ema26 = calcEMA(data, 26);
  const macdLine = ema26.map((d, i) => ({
    time: d.time,
    value: parseFloat((ema12[i].value - d.value).toFixed(2)),
  }));
  const k = 2 / 10;
  let signal = macdLine[0].value;
  const signalLine = macdLine.map(d => {
    signal = d.value * k + signal * (1 - k);
    return { time: d.time, value: parseFloat(signal.toFixed(2)) };
  });
  const histogram = macdLine.map((d, i) => ({
    time: d.time,
    value: parseFloat((d.value - signalLine[i].value).toFixed(2)),
  }));
  return { macdLine, signalLine, histogram };
}

const SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "AAPL", "TSLA", "NVDA"];

export default function TradingChart() {
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef({});
  const dataRef = useRef([]);
  const liveIntervalRef = useRef(null);

  const [selectedSymbol, setSelectedSymbol] = useState("BTC/USDT");
  const [selectedInterval, setSelectedInterval] = useState("1h");
  const [chartType, setChartType] = useState("candlestick");
  const [activeIndicators, setActiveIndicators] = useState({ VOL: true });
  const [theme, setTheme] = useState("dark");
  const [isLive, setIsLive] = useState(false);
  const [crosshairData, setCrosshairData] = useState(null);
  const [priceChange, setPriceChange] = useState({ value: 0, pct: 0 });
  const [LWC, setLWC] = useState(null);
  const [loaded, setLoaded] = useState(false);

  // Load lightweight-charts dynamically
  useEffect(() => {
    const script = document.createElement("script");
    script.src = "https://cdnjs.cloudflare.com/ajax/libs/lightweight-charts/4.1.3/lightweight-charts.standalone.production.js";
    script.onload = () => {
      setLWC(window.LightweightCharts);
      setLoaded(true);
    };
    document.head.appendChild(script);
    return () => document.head.removeChild(script);
  }, []);

  const colors = theme === "dark"
    ? { bg: "#0f1117", grid: "#1e2130", text: "#94a3b8", border: "#1e2130", up: "#26a69a", down: "#ef5350" }
    : { bg: "#ffffff", grid: "#f1f5f9", text: "#475569", border: "#e2e8f0", up: "#16a34a", down: "#dc2626" };

  const buildChart = useCallback(() => {
    if (!LWC || !chartContainerRef.current) return;

    // Destroy old chart
    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
      seriesRef.current = {};
    }

    const container = chartContainerRef.current;
    const chart = LWC.createChart(container, {
      width: container.clientWidth,
      height: container.clientHeight,
      layout: { background: { color: colors.bg }, textColor: colors.text },
      grid: { vertLines: { color: colors.grid }, horzLines: { color: colors.grid } },
      crosshair: { mode: LWC.CrosshairMode.Normal },
      rightPriceScale: { borderColor: colors.border },
      timeScale: { borderColor: colors.border, timeVisible: true, secondsVisible: false },
      handleScroll: true,
      handleScale: true,
    });
    chartRef.current = chart;

    const rawData = generateOHLC(300);
    dataRef.current = rawData;

    // Main series
    let mainSeries;
    if (chartType === "candlestick") {
      mainSeries = chart.addCandlestickSeries({
        upColor: colors.up, downColor: colors.down,
        borderUpColor: colors.up, borderDownColor: colors.down,
        wickUpColor: colors.up, wickDownColor: colors.down,
      });
      mainSeries.setData(rawData);
    } else if (chartType === "bar") {
      mainSeries = chart.addBarSeries({ upColor: colors.up, downColor: colors.down });
      mainSeries.setData(rawData);
    } else {
      mainSeries = chart.addAreaSeries({
        lineColor: "#6366f1", topColor: "rgba(99,102,241,0.3)", bottomColor: "rgba(99,102,241,0.0)", lineWidth: 2,
      });
      mainSeries.setData(rawData.map(d => ({ time: d.time, value: d.close })));
    }
    seriesRef.current.main = mainSeries;

    // Indicators
    if (activeIndicators.SMA) {
      const s = chart.addLineSeries({ color: INDICATORS.SMA.color, lineWidth: 1.5, priceLineVisible: false });
      s.setData(calcSMA(rawData, 20));
      seriesRef.current.SMA = s;
    }
    if (activeIndicators.EMA) {
      const s = chart.addLineSeries({ color: INDICATORS.EMA.color, lineWidth: 1.5, priceLineVisible: false });
      s.setData(calcEMA(rawData, 20));
      seriesRef.current.EMA = s;
    }
    if (activeIndicators.BOLL) {
      const boll = calcBollinger(rawData);
      const addBand = (key, color) => {
        const s = chart.addLineSeries({ color, lineWidth: 1, lineStyle: 2, priceLineVisible: false });
        s.setData(boll.map(d => ({ time: d.time, value: d[key] })));
        seriesRef.current[`BOLL_${key}`] = s;
      };
      addBand("upper", INDICATORS.BOLL.color);
      addBand("middle", "#a78bfa");
      addBand("lower", INDICATORS.BOLL.color);
    }

    // Volume (separate pane)
    if (activeIndicators.VOL) {
      const volSeries = chart.addHistogramSeries({
        color: "#6b728044",
        priceFormat: { type: "volume" },
        priceScaleId: "vol",
        scaleMargins: { top: 0.8, bottom: 0 },
      });
      volSeries.setData(rawData.map(d => ({
        time: d.time,
        value: d.volume,
        color: d.close >= d.open ? colors.up + "66" : colors.down + "66",
      })));
      seriesRef.current.VOL = volSeries;
    }

    // Price change
    const first = rawData[0].close, last = rawData[rawData.length - 1].close;
    setPriceChange({ value: parseFloat((last - first).toFixed(2)), pct: parseFloat(((last - first) / first * 100).toFixed(2)) });

    // Crosshair
    chart.subscribeCrosshairMove(param => {
      if (param.time && seriesRef.current.main) {
        const d = param.seriesData.get(seriesRef.current.main);
        if (d) setCrosshairData(d);
      } else {
        setCrosshairData(null);
      }
    });

    chart.timeScale().fitContent();

    // Resize observer
    const ro = new ResizeObserver(() => {
      if (chartRef.current && container) {
        chartRef.current.applyOptions({ width: container.clientWidth, height: container.clientHeight });
      }
    });
    ro.observe(container);
    return () => ro.disconnect();
  }, [LWC, theme, chartType, activeIndicators, selectedSymbol, selectedInterval]);

  useEffect(() => {
    if (loaded) buildChart();
  }, [loaded, buildChart]);

  // Live price updates
  useEffect(() => {
    if (liveIntervalRef.current) clearInterval(liveIntervalRef.current);
    if (!isLive || !seriesRef.current.main || !dataRef.current.length) return;
    liveIntervalRef.current = setInterval(() => {
      const last = dataRef.current[dataRef.current.length - 1];
      const change = (Math.random() - 0.49) * last.close * 0.003;
      const newClose = parseFloat((last.close + change).toFixed(2));
      const updated = {
        ...last,
        close: newClose,
        high: Math.max(last.high, newClose),
        low: Math.min(last.low, newClose),
      };
      dataRef.current[dataRef.current.length - 1] = updated;
      if (chartType === "area" || chartType === "line") {
        seriesRef.current.main?.update({ time: updated.time, value: updated.close });
      } else {
        seriesRef.current.main?.update(updated);
      }
    }, 800);
    return () => clearInterval(liveIntervalRef.current);
  }, [isLive, chartType]);

  const toggleIndicator = (key) => {
    setActiveIndicators(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const lastPrice = dataRef.current[dataRef.current.length - 1]?.close ?? 0;
  const isPositive = priceChange.pct >= 0;

  const bg = theme === "dark" ? "#0f1117" : "#f8fafc";
  const surface = theme === "dark" ? "#1a1d2e" : "#ffffff";
  const border = theme === "dark" ? "#1e2130" : "#e2e8f0";
  const text = theme === "dark" ? "#e2e8f0" : "#1e293b";
  const muted = theme === "dark" ? "#64748b" : "#94a3b8";
  const accent = "#6366f1";

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", background: bg, color: text, fontFamily: "'JetBrains Mono', 'Fira Code', monospace", fontSize: 12 }}>
      {/* Google Fonts */}
      <style>{`@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap');`}</style>

      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 16, padding: "10px 16px", borderBottom: `1px solid ${border}`, background: surface, flexWrap: "wrap" }}>
        {/* Symbol selector */}
        <select value={selectedSymbol} onChange={e => setSelectedSymbol(e.target.value)}
          style={{ background: bg, color: text, border: `1px solid ${border}`, borderRadius: 6, padding: "5px 10px", fontFamily: "inherit", fontSize: 13, fontWeight: 600, cursor: "pointer" }}>
          {SYMBOLS.map(s => <option key={s}>{s}</option>)}
        </select>

        {/* Price */}
        <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
          <span style={{ fontSize: 20, fontWeight: 700, letterSpacing: -1 }}>{lastPrice.toLocaleString()}</span>
          <span style={{ color: isPositive ? "#26a69a" : "#ef5350", fontWeight: 600, fontSize: 13 }}>
            {isPositive ? "▲" : "▼"} {Math.abs(priceChange.pct)}%
          </span>
        </div>

        {/* Interval buttons */}
        <div style={{ display: "flex", gap: 4 }}>
          {INTERVALS.map(iv => (
            <button key={iv} onClick={() => setSelectedInterval(iv)}
              style={{ padding: "4px 10px", borderRadius: 5, border: `1px solid ${selectedInterval === iv ? accent : border}`, background: selectedInterval === iv ? accent + "22" : "transparent", color: selectedInterval === iv ? accent : muted, cursor: "pointer", fontFamily: "inherit", fontSize: 11, fontWeight: 600, transition: "all 0.15s" }}>
              {iv}
            </button>
          ))}
        </div>

        {/* Chart type */}
        <div style={{ display: "flex", gap: 4 }}>
          {["candlestick", "bar", "area"].map(t => (
            <button key={t} onClick={() => setChartType(t)}
              style={{ padding: "4px 10px", borderRadius: 5, border: `1px solid ${chartType === t ? "#f59e0b" : border}`, background: chartType === t ? "#f59e0b22" : "transparent", color: chartType === t ? "#f59e0b" : muted, cursor: "pointer", fontFamily: "inherit", fontSize: 11, fontWeight: 600, textTransform: "capitalize" }}>
              {t === "candlestick" ? "🕯" : t === "bar" ? "📊" : "📈"} {t}
            </button>
          ))}
        </div>

        <div style={{ marginLeft: "auto", display: "flex", gap: 8, alignItems: "center" }}>
          {/* Live button */}
          <button onClick={() => setIsLive(p => !p)}
            style={{ padding: "5px 12px", borderRadius: 6, border: `1px solid ${isLive ? "#34d399" : border}`, background: isLive ? "#34d39922" : "transparent", color: isLive ? "#34d399" : muted, cursor: "pointer", fontFamily: "inherit", fontSize: 11, fontWeight: 700, display: "flex", alignItems: "center", gap: 5 }}>
            <span style={{ width: 7, height: 7, borderRadius: "50%", background: isLive ? "#34d399" : muted, display: "inline-block", animation: isLive ? "pulse 1s infinite" : "none" }} />
            LIVE
          </button>

          {/* Theme toggle */}
          <button onClick={() => setTheme(t => t === "dark" ? "light" : "dark")}
            style={{ padding: "5px 12px", borderRadius: 6, border: `1px solid ${border}`, background: "transparent", color: muted, cursor: "pointer", fontFamily: "inherit", fontSize: 13 }}>
            {theme === "dark" ? "☀️" : "🌙"}
          </button>
        </div>
      </div>

      {/* Indicators toolbar */}
      <div style={{ display: "flex", gap: 6, padding: "8px 16px", borderBottom: `1px solid ${border}`, background: surface, flexWrap: "wrap", alignItems: "center" }}>
        <span style={{ color: muted, fontSize: 11, marginRight: 4, fontWeight: 600 }}>INDICATORS</span>
        {Object.entries(INDICATORS).map(([key, ind]) => (
          <button key={key} onClick={() => toggleIndicator(key)}
            style={{ padding: "3px 10px", borderRadius: 20, border: `1px solid ${activeIndicators[key] ? ind.color : border}`, background: activeIndicators[key] ? ind.color + "22" : "transparent", color: activeIndicators[key] ? ind.color : muted, cursor: "pointer", fontFamily: "inherit", fontSize: 11, fontWeight: 600, transition: "all 0.15s" }}>
            {ind.label}
          </button>
        ))}
      </div>

      {/* Crosshair OHLCV bar */}
      {crosshairData && (
        <div style={{ display: "flex", gap: 16, padding: "5px 16px", background: theme === "dark" ? "#161929" : "#f1f5f9", borderBottom: `1px solid ${border}`, fontSize: 11 }}>
          {crosshairData.open !== undefined ? (
            <>
              <span>O <b style={{ color: text }}>{crosshairData.open}</b></span>
              <span>H <b style={{ color: "#26a69a" }}>{crosshairData.high}</b></span>
              <span>L <b style={{ color: "#ef5350" }}>{crosshairData.low}</b></span>
              <span>C <b style={{ color: text }}>{crosshairData.close}</b></span>
            </>
          ) : (
            <span>Price <b style={{ color: text }}>{crosshairData.value}</b></span>
          )}
        </div>
      )}

      {/* Chart */}
      <div ref={chartContainerRef} style={{ flex: 1, minHeight: 0 }} />

      {/* Footer */}
      <div style={{ padding: "6px 16px", borderTop: `1px solid ${border}`, background: surface, display: "flex", gap: 20, fontSize: 10, color: muted }}>
        <span>Powered by <b style={{ color: accent }}>Lightweight Charts™</b> (Open Source · No Watermark)</span>
        <span style={{ marginLeft: "auto" }}>Scroll to zoom · Drag to pan · Hover for crosshair</span>
      </div>

      <style>{`
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
        button:hover { filter: brightness(1.15); }
        select:focus { outline: none; }
      `}</style>
    </div>
  );
}
