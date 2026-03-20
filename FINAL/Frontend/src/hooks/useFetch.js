import { useState, useEffect } from "react";

const useFetch = (url, symbol) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!url || !symbol) return;

    const controller = new AbortController();

    const fetchData = async () => {
      setLoading(true);
      try {
        const response = await fetch(url, {
          signal: controller.signal,
        });
        const result = await response.json();
        setData(result);
      } catch (err) {
        if (err.name === "AbortError") return; // 👈 Ignore stale requests
        setError(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();

    return () => controller.abort(); // 👈 Kills pending request on symbol change
  }, [url, symbol]);

  return { data, loading, error };
};

export default useFetch;
