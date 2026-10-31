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
Per klant voorkeuren: taal (Franstalige/anderstalige opdrachten aan/uit; `tenders.language` staat er al), categorie (Marketing/Communicatie/Events/PR/Webdesign, staat al in `tenders.category`), regio (NUTS), minimumscore, en schakelaar "ook Belgische aanbesteders met uitvoering in het buitenland".
Voorbereiding nu: bij opdrachten opslaan of aanbesteder Belgisch is én of uitvoering in BE ligt (nog niet gebouwd). Wachtlijstformulier vraagt nog niet wat een bureau doet.

## Open
- Beslissing 3: "twijfelgevallen kijkt een mens na" (FAQ) uitwerken.
- Beslismoment outreach starten (samen met Filip). Zoekwoord-ruis meten (water/frisdrank, N34-studie kwamen door CPV/zoekwoorden; Haiku filtert).
- Verificaties: link-formaat e-Procurement, TED-dedup.

## Later in de sessie (31 okt, 00:30–01:50)
- Review-flow: zondag 18:00 (17:00 UTC) voorbeeld naar hallo@, maandag 07:00 verzenden zonder opnieuw te scrapen; GitHub-variabelen `DIGEST_EXCLUDE` (codes) en `DIGEST_HOLD=true`. Standaard wordt verzonden (keuze Filip: vergeten mag de digest niet tegenhouden).
- `title_nl` (migratie 005) en `language` (006) via Supabase CLI (`supabase link` gedaan, Filip ingelogd). Digest toont NL-titel + taallabel ("Opdracht in het Frans: de offerte moet ook in het Frans").
- Dedup op titel bij selectie (TED ↔ e-Procurement, geen gedeeld nummer; BOSA's `publicationReferenceNumbersTED` bevat de eigen ref), vóór deadline-filter; dubbels mee als verstuurd gemarkeerd.
- Buitenlandse aanbesteder (TED) → score max 6 (in code, `capped_score`).
- BOSA herverdeling: Filip blijft bij keuze om niets te vragen.

## Vóór de outreach start (beslist Filip 31 okt) — in deze volgorde, samen
1. Layout website + digestmail pimpen: nu te generiek/saai.
2. Product verrijken: wat maakt dat de klant "wow" zegt i.p.v. "ok"? Samen brainstormen.
3. Grondige eindcheck: flow, customer journey, edge cases, fouten/hiaten, aansprakelijkheid (voorwaarden, disclaimers). Pas daarna outreach.
