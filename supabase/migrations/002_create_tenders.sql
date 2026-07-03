-- Kansenradar — Tenders tabel
-- Slaat ruwe + verwerkte overheidsopdrachten op, doorheen de volledige pipeline:
-- scrape -> CPV-filter -> Haiku pre-screen -> Sonnet samenvatting/score -> digest-verzending

CREATE TABLE IF NOT EXISTS tenders (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

    -- Herkomst
    source TEXT NOT NULL,              -- 'ted' | 'e-notification'
    source_ref TEXT NOT NULL UNIQUE,   -- uniek publicatienummer per bron, dedup-sleutel

    -- Ruwe velden (uit scraper, ongewijzigd)
    title TEXT NOT NULL,
    authority TEXT,                    -- aanbestedende overheid
    cpv_codes TEXT[],
    budget_text TEXT,
    deadline DATE,
    url TEXT,
    country TEXT,
    raw JSONB,                         -- volledige ruwe API-respons, voor debugging/herverwerking

    -- Verwerkingsstatus (elke stap alleen op NULL-rijen, voor idempotentie)
    passed_cpv BOOLEAN,
    prescreen_relevant BOOLEAN,
    category TEXT,                     -- 'Communicatie' | 'Marketing' | 'Events' | 'PR' | 'Webdesign'
    summary TEXT,
    score INT,                         -- 1-10
    processed_at TIMESTAMPTZ,

    -- Distributie
    sent_in_digest_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Row Level Security: geen publieke toegang, enkel service role (server-side pipeline)
ALTER TABLE tenders ENABLE ROW LEVEL SECURITY;

-- Dedup bij scrapen: ON CONFLICT (source_ref) DO NOTHING/UPDATE
CREATE UNIQUE INDEX IF NOT EXISTS idx_tenders_source_ref ON tenders(source_ref);

CREATE INDEX IF NOT EXISTS idx_tenders_deadline ON tenders(deadline);

-- Snelle selectie van te versturen tenders in de digest-opbouw
CREATE INDEX IF NOT EXISTS idx_tenders_digest_candidates
    ON tenders(score DESC)
    WHERE sent_in_digest_at IS NULL;
