-- Kansenradar — Nederlandse titel per opdracht
-- title_nl: door Sonnet gegenereerd als de originele titel niet Nederlands is (anders NULL)

ALTER TABLE tenders ADD COLUMN IF NOT EXISTS title_nl TEXT;
