-- Kansenradar — Wachtlijst: interessevraag + bron per kanaal
-- interesse: 'uitproberen' | 'meer-zien' | 'nieuwsgierig'
-- source bestond al (default 'landing_page'); wordt nu gevuld met ?bron= uit de link (bv. 'mail1', 'linkedin')
-- sample_sent_at: tijdstip waarop de bedankmail met voorbeeld-digest verstuurd werd (NULL = niet gelukt)

ALTER TABLE waitlist_signups ADD COLUMN IF NOT EXISTS interesse TEXT;
ALTER TABLE waitlist_signups ADD COLUMN IF NOT EXISTS sample_sent_at TIMESTAMPTZ;
