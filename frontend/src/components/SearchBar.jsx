import { useRef, useEffect, useState } from "react";
import { useSearch } from "../hooks/useStock";

export default function SearchBar({ onSelect }) {
  const { query, results, loading, search, addRecentSearch } = useSearch();
  const wrapRef = useRef(null);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [isFocused, setIsFocused] = useState(false);

  useEffect(() => {
    setActiveIndex(-1);
  }, [results, query]);

  const chooseResult = (item) => {
    const resultSymbol =
      typeof item === "string" ? item : item?.symbol || query || "";
    const next = String(resultSymbol || "").toUpperCase();
    if (!next) return;
    if (item && typeof item === "object") {
      addRecentSearch(item);
    } else {
      addRecentSearch({ symbol: next, name: next, exchange: "NSE" });
    }
    onSelect(next);
    search("");
  };

  const highlightedText = (text, highlight) => {
    const source = String(text || "");
    if (!source) return source;

    if (
      highlight &&
      Number.isInteger(highlight.start) &&
      Number.isInteger(highlight.end)
    ) {
      const start = Math.max(0, Math.min(source.length, highlight.start));
      const end = Math.max(start, Math.min(source.length, highlight.end));
      if (start < end) {
        return (
          <>
            {source.slice(0, start)}
            <mark className="search-mark">{source.slice(start, end)}</mark>
            {source.slice(end)}
          </>
        );
      }
    }

    const token = query.trim();
    if (!token) return source;
    const start = source.toLowerCase().indexOf(token.toLowerCase());
    if (start < 0) return source;
    const end = start + token.length;
    return (
      <>
        {source.slice(0, start)}
        <mark className="search-mark">{source.slice(start, end)}</mark>
        {source.slice(end)}
      </>
    );
  };

  const grouped = {
    recent: results.filter((r) => r?.matchedOn === "recent"),
    popular: results.filter((r) => r?.matchedOn === "popular"),
    search: results.filter(
      (r) => r?.matchedOn !== "recent" && r?.matchedOn !== "popular",
    ),
  };
  const orderedResults = [
    ...grouped.recent,
    ...grouped.popular,
    ...grouped.search,
  ];

  // Close on outside click
  useEffect(() => {
    function handler(e) {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) {
        setIsFocused(false);
        search("");
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [search]);

  const handleKeyDown = (e) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (!orderedResults.length) return;
      setActiveIndex((prev) => (prev + 1) % orderedResults.length);
      return;
    }

    if (e.key === "ArrowUp") {
      e.preventDefault();
      if (!orderedResults.length) return;
      setActiveIndex((prev) =>
        prev <= 0 ? orderedResults.length - 1 : prev - 1,
      );
      return;
    }

    if (e.key === "Escape") {
      setIsFocused(false);
      search("");
      return;
    }

    if (e.key === "Enter" && (query.length >= 1 || activeIndex >= 0)) {
      if (activeIndex >= 0 && activeIndex < orderedResults.length) {
        chooseResult(orderedResults[activeIndex]);
        return;
      }
      chooseResult(query);
    }
  };

  return (
    <div className="search-wrap" ref={wrapRef}>
      <div className="search-box">
        <svg
          className="search-icon"
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input
          className="search-input mono"
          type="text"
          placeholder="Symbol, e.g. TCS, INFY, RELIANCE…"
          value={query}
          onChange={(e) => search(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onKeyDown={handleKeyDown}
          spellCheck={false}
          autoComplete="off"
          role="combobox"
          aria-expanded={isFocused && orderedResults.length > 0}
          aria-controls="stock-search-results"
          aria-activedescendant={
            activeIndex >= 0 ? `stock-search-option-${activeIndex}` : undefined
          }
        />
        {loading && <div className="search-spinner" />}
      </div>

      {isFocused && orderedResults.length > 0 && (
        <div
          className="search-dropdown"
          id="stock-search-results"
          role="listbox"
        >
          {[
            ["Recent", grouped.recent],
            ["Popular", grouped.popular],
            ["Suggestions", grouped.search],
          ].map(([label, items]) => {
            if (!items.length) return null;
            return (
              <div key={label}>
                <div className="search-group-label">{label}</div>
                {items.map((r) => {
                  const idx = orderedResults.indexOf(r);
                  return (
                    <button
                      key={`${r.symbol}:${r.exchange || ""}:${idx}`}
                      id={`stock-search-option-${idx}`}
                      role="option"
                      aria-selected={idx === activeIndex}
                      className={`search-result-item ${idx === activeIndex ? "active" : ""}`}
                      onMouseEnter={() => setActiveIndex(idx)}
                      onClick={() => chooseResult(r)}
                    >
                      <span className="sri-symbol mono">
                        {highlightedText(r.symbol, r?.highlight?.symbol)}
                      </span>
                      <span className="sri-title">
                        {highlightedText(r.title || r.name, r?.highlight?.name)}
                      </span>
                      <span className="sri-exchange mono">
                        {r.exchange || "NSE"}
                      </span>
                    </button>
                  );
                })}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
