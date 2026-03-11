-- =====================================================================
--  Seed RSS feeds into Supabase
--  Run in Supabase → SQL Editor after creating tables
--  Add/remove feeds as needed
-- =====================================================================

INSERT INTO rss_feeds (name, country, category, url, is_active) VALUES
  ('Times of India - Business', 'IN', 'business', 'https://timesofindia.indiatimes.com/rssfeeds/1898055.cms', true),
  ('Times of India - Economy',  'IN', 'economy',  'https://timesofindia.indiatimes.com/rssfeeds/1898570.cms', true),
  ('NDTV Business',             'IN', 'business', 'https://feeds.feedburner.com/ndtvprofit-latest', true),
  ('NDTV Markets',              'IN', 'markets',  'https://www.ndtv.com/rss/markets', true),
  ('The Hindu Business',        'IN', 'business', 'https://www.thehindu.com/business/feeder/default.rss', true),
  ('Moneycontrol Latest',       'IN', 'markets',  'https://www.moneycontrol.com/rss/latestnews.xml', true),
  ('Economic Times Markets',    'IN', 'markets',  'https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms', true),
  ('Economic Times Economy',    'IN', 'economy',  'https://economictimes.indiatimes.com/economy/rssfeeds/1373380680.cms', true),
  ('Livemint Markets',          'IN', 'markets',  'https://www.livemint.com/rss/markets', true),
  ('Business Standard Markets', 'IN', 'markets',  'https://www.business-standard.com/rss/markets-106.rss', true)
ON CONFLICT (url) DO NOTHING;

-- Verify:
-- SELECT * FROM rss_feeds;