-- ─────────────────────────────────────────────────────────────────────────────
-- 1. campaigns tablosunu oluştur
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS campaigns (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_email    text NOT NULL,
  handle        text NOT NULL,
  spend_tier    text NOT NULL,   -- gifted | under100 | 100-500 | 500-2k | 2k+
  outcome       text NOT NULL,   -- worth_it | meh | waste
  campaign_date date NOT NULL DEFAULT CURRENT_DATE,
  orders_range  text,            -- 0 | 1-5 | 5-20 | 20+  (optional)
  notes         text,
  status        text NOT NULL DEFAULT 'logged',   -- logged | completed
  created_at    timestamptz NOT NULL DEFAULT now()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. analyses tablosuna user_email kolonu ekle
--    (eğer zaten varsa hata vermez)
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS user_email text;
CREATE INDEX IF NOT EXISTS analyses_user_email_idx ON analyses (user_email);
