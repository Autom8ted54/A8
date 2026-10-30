-- Kansenradar — taal van de opdracht (en dus van de offerte)
-- language: 'nl' | 'fr' | 'en' | 'de' | 'andere' — door Sonnet bepaald

ALTER TABLE tenders ADD COLUMN IF NOT EXISTS language TEXT;
