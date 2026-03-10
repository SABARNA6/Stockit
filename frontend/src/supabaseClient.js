import { createClient } from "@supabase/supabase-js";

// ─── Replace these with your Supabase project credentials ────────────────────
// Found at: https://supabase.com/dashboard → your project → Settings → API
const SUPABASE_URL = "https://jfgenjpkachgssbsxzzf.supabase.co";
const SUPABASE_ANON_KEY = "sb_publishable_z27ATYTCE1sSyeTVNvD7SA_spK23_iH";

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
  auth: {
    flowType: "pkce", // ← tokens exchanged server-side, never in URL
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: true, // ← clears the token from URL after reading
  },
});
