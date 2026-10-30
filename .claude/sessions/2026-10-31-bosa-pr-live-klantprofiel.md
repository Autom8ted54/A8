# 2026-10-30/31 — BOSA productie live, Actions-run, klantprofiel-plan

## Gedaan
- BOSA activeerde Production (30 okt). `EPROC_ENV=PR` lokaal getest: 23-24 relevante oproepen uit ~2700 publicaties (14 dagen). Dry-run: 24 pre-screened, 14 samengevat (score 5-8).
- 11 GitHub-secrets gezet (repo Autom8ted54/A8) door Filip via `gh secret set` uit `.env`.
- Workflow: cron nu enkel maandag 06:00 UTC; handmatige run heeft `dry_run`-input (standaard aan). GitHub-run OK in 44s: BOSA laat Actions-IP's toe.
- Keep-alive verhuisd naar `.github/workflows/supabase-keepalive.yml` (dagelijks); LaunchAgent + `ops/` weg.
- Sample-digest hergenereerd en gedeployed. Site-beloftes aangepast: één digest voor iedereen (geen "op maat / jouw sector en regio" meer).

## Beslissingen Filip
- Digest per bureau: fase 1 = één digest voor iedereen (A), maar bouwen met filtering per klant in het achterhoofd.
- Buitenlandse opdrachten: keuze laten aan de klant (profielvoorkeur); standaard = plaats van uitvoering BE (TED-filter `place-of-performance IN (BEL)`).

## Plan klantprofiel (later, wanneer er echte inschrijvingen zijn)
Per klant voorkeuren: categorie (Marketing/Communicatie/Events/PR/Webdesign, staat al in `tenders.category`), regio (NUTS), minimumscore, en schakelaar "ook Belgische aanbesteders met uitvoering in het buitenland".
Voorbereiding nu: bij opdrachten opslaan of aanbesteder Belgisch is én of uitvoering in BE ligt (nog niet gebouwd). Wachtlijstformulier vraagt nog niet wat een bureau doet.

## Open
- Beslissing 3: "twijfelgevallen kijkt een mens na" (FAQ) uitwerken.
- Beslismoment outreach starten (samen met Filip). Zoekwoord-ruis meten (water/frisdrank, N34-studie kwamen door CPV/zoekwoorden; Haiku filtert).
- Verificaties: link-formaat e-Procurement, TED-dedup.
