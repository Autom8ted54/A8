# 2026-10-29 — BOSA-credentials, e-Procurement-scraper, Supabase-herstel

## Wat er gebeurde
- BOSA stuurde Media-credentials (INT + PR, docx). Via script naar `.env` (`EPROC_INT_*`, `EPROC_PR_*`) zonder tonen; docx in `.gitignore`.
- INT getest: token + zoek-API werken. Filip mailde BOSA (16:35) → PR-activering gevraagd. Bewust géén vraag over herverdeling (keuze Filip); wel: geen persoonsgegevens in digest, meteen bijsturen als BOSA iets vraagt. Overeenkomst nagelezen: verbod op doorgeven aan derden gaat over persoons-/vertrouwelijke gegevens.
- `scraper/e_procurement.py` gebouwd + in pijplijn (TED-dedup, bron-faalt → digest gaat door + alert). AI-stap leest nu ook e-Procurement-omschrijvingen. Events via zoekwoorden (FAQ-belofte).
- Supabase-project bleek gepauzeerd (±2 weken) → wachtlijstformulier lag plat. Filip herstartte; keep-alive LaunchAgent (`ops/`) door Filip geïnstalleerd.
- Eerste volledige dry-run met echte keys (TED): werkt. Digest-fixes: TED-titelprefix weg, bronregel enkel echte bronnen, "deze week".
- Formuliertest (source=test, pasmansfilip@gmail.com): OK, bedankmail verzonden. **0 echte inschrijvingen op de wachtlijst.**
- Commits: 209223a, bfe5475.

## Learnings
- BOSA eProcurementSea-API: `page` verplicht, pageSize ≤100, header `BelGov-Trace-Id` verplicht, onbekende params worden stil genegeerd (elke filter verifiëren via totalCount), `cpvCodes` = exacte match. Details: sessienotitie 2026-10-23.
- Supabase free tier pauzeert na 7 dagen zonder activiteit → DNS geeft NXDOMAIN; na restore eerst 521, ±5 min tot REST werkt.
- Auto-mode blokkeert LaunchAgents installeren ("Unauthorized Persistence") → bestanden klaarzetten, Filip activeert met `!`.
- Credentials uit een document halen: eerst structuur bekijken met gemaskeerde waarden, dan rechtstreeks naar `.env` schrijven en enkel lengtes tonen.
- Visuele check van de digest (headless Chrome) vond 3 problemen die tests niet vingen, o.a. een foute bronclaim.

## Geen correcties door Filip deze sessie

## Open
- Wachten op PR-activering BOSA → dan: `EPROC_ENV=PR` lokaal testen; link-formaat, TED-dedup en GitHub Actions-IP verifiëren; zoekwoord-precisie meten; GitHub secrets (Filip) + dry-run.
- `site/api/sample-digest.html` hergenereren + deploy door Filip.
- Beslissingen Filip: digest per bureau (sector/regio, beloofd op site); buitenlandse opdrachten met uitvoering in BE houden?; "twijfelgevallen kijkt een mens na" (FAQ) uitwerken.
- Keep-alive weghalen zodra de wekelijkse digest in GitHub Actions draait.
- Niet gepusht naar GitHub.
- `.tmp.driveupload/` in projectmap (Google Drive?) — niet van ons, laten staan.
