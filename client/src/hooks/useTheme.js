import { useState, useEffect } from "react";

const STORAGE_KEY = "marketlens-theme";
const DEFAULT     = "dark";

export function useTheme() {
  const [theme, setThemeState] = useState(() => {
    // 1. Check localStorage first
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored === "light" || stored === "dark") return stored;
    } catch {}
    // 2. Respect system preference
    if (typeof window !== "undefined" &&
        window.matchMedia("(prefers-color-scheme: light)").matches) {
      return "light";
    }
    return DEFAULT;
  });

  // Apply to <html> element as a data attribute
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try { localStorage.setItem(STORAGE_KEY, theme); } catch {}
  }, [theme]);

  // Listen for system preference changes while no override is stored
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: light)");
    const handler = (e) => {
      try {
        if (!localStorage.getItem(STORAGE_KEY)) {
          setThemeState(e.matches ? "light" : "dark");
        }
      } catch {}
    };
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  const toggle = () => setThemeState(t => t === "dark" ? "light" : "dark");
  const setTheme = (t) => setThemeState(t);

  return { theme, toggle, setTheme, isDark: theme === "dark" };
}
