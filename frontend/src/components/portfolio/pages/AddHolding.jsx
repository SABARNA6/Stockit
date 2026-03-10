import { useState, useRef } from "react";
import { supabase } from "../../../supabaseClient";
import PageHeader from "../common/PageHeader";
import { Icon } from "../utils";

export default function AddHoldingPage({ userId, onSaved }) {
  const [tab, setTab] = useState("manual");
  const [rows, setRows] = useState([{ symbol: "", qty: "", avg_cost: "" }]);
  const [csv, setCsv] = useState("");
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState({ type: "", text: "" });
  const fileRef = useRef();

  const addRow = () =>
    setRows((r) => [...r, { symbol: "", qty: "", avg_cost: "" }]);

  const removeRow = (i) => setRows((r) => r.filter((_, j) => j !== i));

  const update = (i, f, v) =>
    setRows((r) => r.map((row, j) => (j === i ? { ...row, [f]: v } : row)));

  const parseCSV = (text) => {
    const lines = text.trim().split("\n").filter(Boolean);
    return lines
      .slice(1)
      .map((l) => {
        const [symbol, qty, avg_cost] = l.split(",").map((s) => s.trim());
        return {
          symbol: symbol?.toUpperCase(),
          qty: parseFloat(qty),
          avg_cost: parseFloat(avg_cost),
        };
      })
      .filter((r) => r.symbol && !isNaN(r.qty) && !isNaN(r.avg_cost));
  };

  const handleSave = async () => {
    setMsg({ type: "", text: "" });
    setSaving(true);
    try {
      let data =
        tab === "manual"
          ? rows
              .filter((r) => r.symbol && r.qty && r.avg_cost)
              .map((r) => ({
                user_id: userId,
                symbol: r.symbol.toUpperCase(),
                qty: parseFloat(r.qty),
                avg_cost: parseFloat(r.avg_cost),
              }))
          : parseCSV(csv).map((r) => ({ ...r, user_id: userId }));

      if (!data.length)
        throw new Error("Nothing to save. Fill at least one row.");

      const { error } = await supabase.from("portfolio").insert(data);
      if (error) throw error;

      setMsg({
        type: "success",
        text: `✓ ${data.length} holding${data.length > 1 ? "s" : ""} saved successfully.`,
      });
      setRows([{ symbol: "", qty: "", avg_cost: "" }]);
      setCsv("");
      onSaved();
    } catch (err) {
      setMsg({ type: "error", text: `⚠ ${err.message}` });
    }
    setSaving(false);
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 20,
        animation: "fadeUp .35s ease both",
        maxWidth: 620,
      }}
    >
      <PageHeader
        iconKey="plus"
        title="Add Holdings"
        sub="Track your investments — stored securely in your account"
      />

      {/* Tabs */}
      <div
        style={{
          display: "flex",
          background: "var(--bg-elevated)",
          borderRadius: 8,
          padding: 3,
          width: "fit-content",
          border: "1px solid var(--border)",
        }}
      >
        {[
          ["manual", "Manual Entry"],
          ["csv", "CSV / Paste"],
        ].map(([id, label]) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            style={{
              padding: "7px 18px",
              background: tab === id ? "var(--bg-card)" : "transparent",
              border: "none",
              borderRadius: 6,
              color: tab === id ? "var(--text-primary)" : "var(--text-muted)",
              fontFamily: "var(--mono)",
              fontSize: 11,
              cursor: "pointer",
              letterSpacing: "0.08em",
              transition: "all .15s",
            }}
          >
            {label}
          </button>
        ))}
      </div>

      <div
        style={{
          background: "var(--bg-card)",
          border: "1px solid var(--border)",
          borderRadius: 12,
          padding: 24,
          display: "flex",
          flexDirection: "column",
          gap: 16,
        }}
      >
        {msg.text && (
          <div
            style={{
              padding: "10px 14px",
              background:
                msg.type === "success" ? "var(--green-bg)" : "var(--red-bg)",
              border: `1px solid ${
                msg.type === "success" ? "var(--green)" : "var(--red)"
              }`,
              borderRadius: 8,
              fontSize: 12,
              color: msg.type === "success" ? "var(--green)" : "var(--red)",
              fontFamily: "var(--mono)",
            }}
          >
            {msg.text}
          </div>
        )}

        {tab === "manual" && (
          <>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 90px 130px 36px",
                gap: 8,
              }}
            >
              {["SYMBOL", "QTY", "AVG COST (₹)", ""].map((h, i) => (
                <span
                  key={i}
                  style={{
                    fontSize: 9,
                    letterSpacing: "0.15em",
                    color: "var(--text-muted)",
                    fontFamily: "var(--mono)",
                    paddingLeft: 4,
                  }}
                >
                  {h}
                </span>
              ))}
            </div>

            {rows.map((row, i) => (
              <div
                key={i}
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 90px 130px 36px",
                  gap: 8,
                }}
              >
                {[
                  ["symbol", "e.g. TCS"],
                  ["qty", "50"],
                  ["avg_cost", "3450"],
                ].map(([f, ph]) => (
                  <input
                    key={f}
                    value={row[f]}
                    onChange={(e) => update(i, f, e.target.value)}
                    placeholder={ph}
                    style={{
                      background: "var(--bg-elevated)",
                      border: "1px solid var(--border)",
                      borderRadius: 6,
                      color: "var(--text-primary)",
                      fontFamily: "var(--mono)",
                      fontSize: 12,
                      padding: "9px 11px",
                      outline: "none",
                      width: "100%",
                      transition: "border-color .15s",
                    }}
                    onFocus={(e) =>
                      (e.target.style.borderColor = "var(--green)")
                    }
                    onBlur={(e) =>
                      (e.target.style.borderColor = "var(--border)")
                    }
                  />
                ))}
                <button
                  onClick={() => removeRow(i)}
                  disabled={rows.length === 1}
                  style={{
                    background: "var(--red-bg)",
                    border: "1px solid var(--red)",
                    borderRadius: 6,
                    color: "var(--red)",
                    cursor: rows.length === 1 ? "not-allowed" : "pointer",
                    fontSize: 16,
                    fontWeight: 700,
                    opacity: rows.length === 1 ? 0.4 : 1,
                  }}
                >
                  ×
                </button>
              </div>
            ))}

            <button
              onClick={addRow}
              style={{
                padding: "9px 0",
                background: "transparent",
                border: "1px dashed var(--border-light)",
                borderRadius: 6,
                color: "var(--text-muted)",
                fontFamily: "var(--mono)",
                fontSize: 11,
                cursor: "pointer",
                letterSpacing: "0.08em",
                transition: "all .15s",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = "var(--green)";
                e.currentTarget.style.color = "var(--green)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "var(--border-light)";
                e.currentTarget.style.color = "var(--text-muted)";
              }}
            >
              + Add Row
            </button>
          </>
        )}

        {tab === "csv" && (
          <>
            <div
              style={{
                background: "var(--bg-elevated)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                padding: 12,
                fontSize: 11,
                fontFamily: "var(--mono)",
                color: "var(--text-muted)",
                lineHeight: 2,
              }}
            >
              <div style={{ color: "var(--green)", marginBottom: 2 }}>
                Expected format (header required):
              </div>
              <div>Symbol,Qty,Avg Cost</div>
              <div>TCS,50,3450</div>
              <div>HCLTECH,30,1620</div>
            </div>

            <button
              onClick={() => fileRef.current?.click()}
              style={{
                padding: "9px 0",
                background: "var(--blue-bg)",
                border: "1px solid var(--blue)",
                borderRadius: 8,
                color: "var(--blue)",
                fontFamily: "var(--mono)",
                fontSize: 11,
                cursor: "pointer",
                letterSpacing: "0.08em",
              }}
            >
              📎 Upload CSV / Excel file
            </button>
            <input
              ref={fileRef}
              type="file"
              accept=".csv,.txt"
              style={{ display: "none" }}
              onChange={(e) => {
                const r = new FileReader();
                r.onload = (ev) => setCsv(ev.target.result);
                r.readAsText(e.target.files[0]);
              }}
            />
            <span
              style={{
                fontSize: 10,
                color: "var(--text-muted)",
                textAlign: "center",
                fontFamily: "var(--mono)",
              }}
            >
              — or paste below —
            </span>
            <textarea
              value={csv}
              onChange={(e) => setCsv(e.target.value)}
              rows={6}
              placeholder={"Symbol,Qty,Avg Cost\nTCS,50,3450"}
              style={{
                background: "var(--bg-elevated)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                color: "var(--text-primary)",
                fontFamily: "var(--mono)",
                fontSize: 12,
                padding: 12,
                resize: "vertical",
                outline: "none",
                lineHeight: 1.8,
              }}
            />
          </>
        )}

        <button
          onClick={handleSave}
          disabled={saving}
          style={{
            padding: "13px 0",
            background: "var(--green)",
            border: "none",
            borderRadius: 8,
            color: "#fff",
            fontFamily: "var(--mono)",
            fontSize: 13,
            fontWeight: 700,
            cursor: saving ? "not-allowed" : "pointer",
            letterSpacing: "0.1em",
            opacity: saving ? 0.7 : 1,
            transition: "opacity .2s",
          }}
        >
          {saving ? "Saving..." : "▲ Save to Portfolio"}
        </button>
      </div>
    </div>
  );
}
