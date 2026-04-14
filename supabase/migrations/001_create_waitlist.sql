-- Kansenradar — Wachtlijst tabel
-- Run this in the Supabase SQL editor or via supabase db push

CREATE TABLE IF NOT EXISTS waitlist_signups (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    -- Segmentatievragen
    schrijft_al_in TEXT,           -- 'ja' | 'nee' | 'soms'
    uren_per_week TEXT,            -- '0', '1-2', '3-5', '5+'
    gebruikt_tool TEXT,            -- 'ja-tenderwolf', 'ja-andere', 'nee'
    grootste_frustratie TEXT,      -- Open tekstveld
    aantal_medewerkers TEXT,       -- '1-5', '6-15', '16-30', '30+'
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    source TEXT DEFAULT 'landing_page'
);

-- Row Level Security: geen publieke toegang
-- Alleen de service role (server-side) kan records invoegen
ALTER TABLE waitlist_signups ENABLE ROW LEVEL SECURITY;

-- Geen policies = geen publieke toegang
-- De Cloudflare Function gebruikt de service role key die RLS bypast

-- Index op email voor snelle duplicate check
CREATE INDEX IF NOT EXISTS idx_waitlist_email ON waitlist_signups(email);

-- Index op created_at voor chronologisch ophalen
CREATE INDEX IF NOT EXISTS idx_waitlist_created_at ON waitlist_signups(created_at DESC);
