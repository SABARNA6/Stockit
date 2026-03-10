// src/AuthCallback.jsx
import { useEffect } from "react";
import { supabase } from "./supabaseClient";

export default function AuthCallback() {
  useEffect(() => {
    // Supabase exchanges the code for a session, clears the URL
    supabase.auth.exchangeCodeForSession(window.location.href).then(() => {
      window.location.replace("/"); // redirect to home cleanly
    });
  }, []);

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--bg-primary)",
      }}
    >
      <span
        style={{
          fontFamily: "var(--mono)",
          color: "var(--text-muted)",
          fontSize: 12,
          letterSpacing: "0.1em",
        }}
      >
        Signing you in...
      </span>
    </div>
  );
}
