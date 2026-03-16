import { useState } from "react";
import PageHeader from "../common/PageHeader";
import { Icon, mockLTP } from "../utils";

export default function WatchlistPage({ items, onDelete, onAdd }) {
  const [symbol, setSymbol] = useState("");
  const [name, setName] = useState("");
  const [sector, setSector] = useState("");
  const [price, setPrice] = useState("");
  const [adding, setAdding] = useState(false);
  const [showForm, setShowForm] = useState(false);

  const handleAdd = async () => {
    if (!symbol) return;
    setAdding(true);
    await onAdd({
      symbol: symbol.toUpperCase(),
      name,
      sector,
      price: parseFloat(price) || null,
    });
    setSymbol("");
    setName("");
    setSector("");
    setPrice("");
    setShowForm(false);
    setAdding(false);
  };

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
        iconKey="star"
        title="Watchlist"
        sub={`${items.length} stocks on your radar`}
        action={
          <button
            onClick={() => setShowForm((f) => !f)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "8px 16px",
              background: showForm ? "var(--bg-elevated)" : "var(--amber-bg)",
              border: `1px solid ${
                showForm ? "var(--border)" : "var(--amber)"
              }`,
              borderRadius: 8,
              color: showForm ? "var(--text-muted)" : "var(--amber)",
              fontFamily: "var(--mono)",
              fontSize: 11,
              cursor: "pointer",
              letterSpacing: "0.1em",
            }}
          >
            {showForm ? Icon.close : Icon.plus}{" "}
            {showForm ? "Cancel" : "Add Stock"}
          </button>
        }
      />

      {/* Quick-add form */}
      {showForm && (
        <div
          style={{
            background: "var(--bg-card)",
            border: "1px solid var(--amber)",
            borderRadius: 12,
            padding: 20,
            display: "flex",
            flexDirection: "column",
            gap: 12,
            animation: "fadeUp .2s ease both",
          }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr 1fr 1fr",
              gap: 10,
            }}
          >
            {[
              ["Symbol", "symbol", symbol, setSymbol, "INFY"],
              ["Company Name", "name", name, setName, "Infosys Ltd"],
              ["Sector", "sector", sector, setSector, "IT"],
              ["Target Price ₹", "price", price, setPrice, "1900"],
            ].map(([label, _, val, set, ph]) => (
              <div
                key={label}
                style={{ display: "flex", flexDirection: "column", gap: 5 }}
              >
                <span
                  style={{
                    fontSize: 9,
                    letterSpacing: "0.15em",
                    color: "var(--text-muted)",
                    fontFamily: "var(--mono)",
                    textTransform: "uppercase",
                  }}
                >
                  {label}
                </span>
                <input
                  value={val}
                  onChange={(e) => set(e.target.value)}
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
                    transition: "border-color .15s",
                  }}
                  onFocus={(e) => (e.target.style.borderColor = "var(--amber)")}
                  onBlur={(e) => (e.target.style.borderColor = "var(--border)")}
                />
              </div>
            ))}
          </div>
          <button
            onClick={handleAdd}
            disabled={adding || !symbol}
            style={{
              padding: "10px 0",
              background: "var(--amber)",
              border: "none",
              borderRadius: 8,
              color: "#fff",
              fontFamily: "var(--mono)",
              fontSize: 12,
              fontWeight: 700,
              cursor: adding || !symbol ? "not-allowed" : "pointer",
              letterSpacing: "0.1em",
              opacity: !symbol ? 0.5 : 1,
            }}
          >
            {adding ? "Adding..." : "★ Add to Watchlist"}
          </button>
        </div>
      )}

      {items.length === 0 ? (
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
          <div style={{ fontSize: 32, marginBottom: 12 }}>⭐</div>
          Your watchlist is empty. Add stocks you want to track.
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill,minmax(260px,1fr))",
            gap: 14,
          }}
        >
          {items.map((item) => {
            const ltp = mockLTP(item.symbol, item.price || 1000);
            const diff = item.price
              ? (((ltp - item.price) / item.price) * 100).toFixed(1)
              : null;
            return (
              <div
                key={item.id}
                style={{
                  background: "var(--bg-card)",
                  border: "1px solid var(--border)",
                  borderRadius: 12,
                  padding: 18,
                  display: "flex",
                  flexDirection: "column",
                  gap: 10,
                  transition: "border-color .15s, transform .15s",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = "var(--amber)";
                  e.currentTarget.style.transform = "translateY(-2px)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "var(--border)";
                  e.currentTarget.style.transform = "none";
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                  }}
                >
                  <div>
                    <div
                      style={{
                        fontFamily: "var(--mono)",
                        fontSize: 14,
                        fontWeight: 700,
                        color: "var(--text-primary)",
                      }}
                    >
                      {item.symbol}
                    </div>
                    {item.name && (
                      <div
                        style={{
                          fontSize: 11,
                          color: "var(--text-secondary)",
                          marginTop: 2,
                        }}
                      >
                        {item.name}
                      </div>
                    )}
                  </div>
                  <button
                    onClick={() => onDelete(item.id)}
                    style={{
                      background: "transparent",
                      border: "none",
                      color: "var(--text-muted)",
                      cursor: "pointer",
                      padding: 2,
                    }}
                    onMouseEnter={(e) =>
                      (e.currentTarget.style.color = "var(--red)")
                    }
                    onMouseLeave={(e) =>
                      (e.currentTarget.style.color = "var(--text-muted)")
                    }
                  >
                    {Icon.trash}
                  </button>
                </div>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <span
                    style={{
                      fontFamily: "var(--mono)",
                      fontSize: 14,
                      fontWeight: 600,
                      color: "var(--text-primary)",
                    }}
                  >
                    ₹{ltp.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
                  </span>
                  {item.sector && (
                    <span
                      style={{
                        fontSize: 9,
                        padding: "2px 8px",
                        borderRadius: 20,
                        background: "var(--blue-bg)",
                        color: "var(--blue)",
                        fontFamily: "var(--mono)",
                        letterSpacing: "0.08em",
                      }}
                    >
                      {item.sector}
                    </span>
                  )}
                </div>
                {/* ✅ FIXED: Moved INSIDE the map return, using correct 'price' field */}
                {item.price && (
                  <div
                    style={{
                      fontSize: 11,
                      fontFamily: "var(--mono)",
                      color: diff >= 0 ? "var(--green)" : "var(--red)",
                    }}
                  >
                    Target ₹{item.price.toLocaleString("en-IN")} ·{" "}
                    {diff >= 0 ? "▲" : "▼"}
                    {Math.abs(diff)}% from target
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
