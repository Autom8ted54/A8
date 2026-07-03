-- Kansenradar — Subscribers tabel
-- Betalende/founding member ontvangers van de dagelijkse digest.
-- Los van waitlist_signups: wachtlijst != actieve klant.

CREATE TABLE IF NOT EXISTS subscribers (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    naam TEXT,
    plan TEXT,                         -- 'founding' | 'starter' | 'pro'
    active BOOLEAN DEFAULT true,
    unsubscribe_token UUID DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Row Level Security: geen publieke toegang, enkel service role (server-side pipeline)
ALTER TABLE subscribers ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_subscribers_email ON subscribers(email);
CREATE INDEX IF NOT EXISTS idx_subscribers_unsubscribe_token ON subscribers(unsubscribe_token);
