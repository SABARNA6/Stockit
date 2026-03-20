import { useRef, useEffect } from "react";
import { useSearch } from "../hooks/useStock";

export default function SearchBar({ onSelect }) {
  const { query, results, loading, search } = useSearch();
  const wrapRef = useRef(null);

  // Close on outside click
  useEffect(() => {
    function handler(e) {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) search("");
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [search]);

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && query.length >= 1) {
      onSelect(query.toUpperCase());
      search("");
    }
  };

  return (
    <div className="search-wrap" ref={wrapRef}>
      <div className="search-box">
        <svg className="search-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input
          className="search-input mono"
          type="text"
          placeholder="Symbol, e.g. TCS, INFY, RELIANCE…"
          value={query}
          onChange={e => search(e.target.value)}
          onKeyDown={handleKeyDown}
          spellCheck={false}
          autoComplete="off"
        />
        {loading && <div className="search-spinner" />}
      </div>

      {results.length > 0 && (
        <div className="search-dropdown">
          {results.map((r, i) => (
            <button
              key={i}
              className="search-result-item"
              onClick={() => { onSelect(r.symbol || query.toUpperCase()); search(""); }}
            >
              <span className="sri-symbol mono">{r.symbol}</span>
              <span className="sri-title">{r.title || r.name}</span>
              {r.sentiment && (
                <span className={`sri-sentiment ${r.sentiment.toLowerCase()}`}>{r.sentiment}</span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
