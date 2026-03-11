-- =====================================================================
--  NEWS IMPACT PIPELINE — Supabase Schema
--  Run this entire file in Supabase → SQL Editor → Run
-- =====================================================================


-- ── 1. RSS Feed Sources ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS rss_feeds (
  id          SERIAL PRIMARY KEY,
  name        TEXT NOT NULL,
  country     TEXT DEFAULT 'IN',
  category    TEXT,
  url         TEXT NOT NULL UNIQUE,
  is_active   BOOLEAN DEFAULT true,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── 2. RSS Pool (all fetched articles) ───────────────────────────────
CREATE TABLE IF NOT EXISTS rss_pool (
  id            SERIAL PRIMARY KEY,
  title         TEXT NOT NULL,
  link          TEXT NOT NULL UNIQUE,
  summary       TEXT,
  published_date TEXT,
  source        TEXT,
  rss_id        INTEGER REFERENCES rss_feeds(id),
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rss_pool_link       ON rss_pool(link);
CREATE INDEX IF NOT EXISTS idx_rss_pool_created_at ON rss_pool(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_rss_pool_source     ON rss_pool(source);

-- ── 3. Pool Logs (RSS fetch history) ─────────────────────────────────
CREATE TABLE IF NOT EXISTS pool_logs (
  id          SERIAL PRIMARY KEY,
  rss_id      INTEGER,
  source      TEXT,
  status      TEXT,
  new_items   INTEGER DEFAULT 0,
  skipped     INTEGER DEFAULT 0,
  total_pool  INTEGER DEFAULT 0,
  message     TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── 4. NSE Stocks ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS nse_stocks (
  id           SERIAL PRIMARY KEY,
  ticker       TEXT NOT NULL UNIQUE,
  company_name TEXT,
  industry     TEXT,
  series       TEXT,
  isin         TEXT,
  created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nse_stocks_ticker   ON nse_stocks(ticker);
CREATE INDEX IF NOT EXISTS idx_nse_stocks_industry ON nse_stocks(industry);

-- ── 5. L1 Logs (NLP results) ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS l1_logs (
  id              SERIAL PRIMARY KEY,
  news_id         BIGINT,
  title           TEXT,
  tickers_found   TEXT,
  event_type      TEXT,
  themes          TEXT,
  sentiment       TEXT,
  urgency_score   FLOAT,
  relevance_score FLOAT,
  source          TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_l1_logs_news_id    ON l1_logs(news_id);
CREATE INDEX IF NOT EXISTS idx_l1_logs_event_type ON l1_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_l1_logs_created_at ON l1_logs(created_at DESC);

-- ── 6. L2 Logs (Impact propagation) ──────────────────────────────────
CREATE TABLE IF NOT EXISTS l2_logs (
  id          SERIAL PRIMARY KEY,
  news_id     BIGINT,
  news_title  TEXT,
  ticker      TEXT,
  company     TEXT,
  industry    TEXT,
  impact_type TEXT,
  direction   TEXT,
  confidence  FLOAT,
  reason      TEXT,
  sentiment   TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_l2_logs_ticker     ON l2_logs(ticker);
CREATE INDEX IF NOT EXISTS idx_l2_logs_news_id    ON l2_logs(news_id);
CREATE INDEX IF NOT EXISTS idx_l2_logs_direction  ON l2_logs(direction);
CREATE INDEX IF NOT EXISTS idx_l2_logs_created_at ON l2_logs(created_at DESC);

-- ── 7. L3 Logs (Price predictions) ───────────────────────────────────
CREATE TABLE IF NOT EXISTS l3_logs (
  id                 SERIAL PRIMARY KEY,
  news_id            BIGINT,
  news_title         TEXT,
  ticker             TEXT,
  company            TEXT,
  alert_priority     TEXT,
  direction          TEXT,
  move_estimate_pct  FLOAT,
  move_range_low     FLOAT,
  move_range_high    FLOAT,
  confidence         FLOAT,
  time_horizon       TEXT,
  current_price      FLOAT,
  trend_8d_pct       FLOAT,
  volatility         FLOAT,
  reasoning          TEXT,
  key_risks          TEXT,
  created_at         TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_l3_logs_ticker         ON l3_logs(ticker);
CREATE INDEX IF NOT EXISTS idx_l3_logs_alert_priority ON l3_logs(alert_priority);
CREATE INDEX IF NOT EXISTS idx_l3_logs_direction      ON l3_logs(direction);
CREATE INDEX IF NOT EXISTS idx_l3_logs_created_at     ON l3_logs(created_at DESC);

-- ── 8. Pipeline Progress ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS pipeline_progress (
  id                    SERIAL PRIMARY KEY,
  last_processed_index  INTEGER DEFAULT 0,
  total_articles        INTEGER DEFAULT 0,
  total_relevant        INTEGER DEFAULT 0,
  status                TEXT DEFAULT 'NOT STARTED',
  last_run              TIMESTAMPTZ
);

-- Insert default row
INSERT INTO pipeline_progress
  (last_processed_index, total_articles, total_relevant, status)
VALUES (0, 0, 0, 'NOT STARTED')
ON CONFLICT DO NOTHING;


-- =====================================================================
--  USEFUL QUERIES (for reference)
-- =====================================================================

-- Top IMMEDIATE alerts today:
-- SELECT ticker, company, direction, move_estimate_pct, confidence, reasoning
-- FROM l3_logs
-- WHERE alert_priority = 'IMMEDIATE'
--   AND created_at > NOW() - INTERVAL '24 hours'
-- ORDER BY confidence DESC;

-- All predictions for a specific ticker:
-- SELECT * FROM l3_logs WHERE ticker = 'HDFCBANK' ORDER BY created_at DESC;

-- Most impacted stocks by news today:
-- SELECT ticker, COUNT(*) as mentions, AVG(confidence) as avg_conf
-- FROM l2_logs
-- WHERE created_at > NOW() - INTERVAL '24 hours'
-- GROUP BY ticker ORDER BY mentions DESC;