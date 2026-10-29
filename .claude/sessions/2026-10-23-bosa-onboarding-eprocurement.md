# 2026-10-23 — BOSA-onboarding e-Procurement (Media-account)

## Wat er gebeurde
- BOSA antwoordde op ticket CS0226743 (Maxence Fatrez): **Media-account** = enkel publieke data lezen. Nodig: onboardingformulier + ondertekende FSB-gebruiksovereenkomst.
- Claude vulde in:
  - `~/Downloads/eProc Technical Connection Request_Media - Autom8ted.docx` (Autom8ted, BE 1037.472.507, Singel 26 2640 Mortsel, +32 479 51 15 57; auth-mail api@kansenradar.be; ±50 gem./±500 max. requests/dag; contact Filip Pasmans, hallo@, NL)
  - `GO Webservices DIS v6.3.2 NL - ingevuld.pdf` p.16 (datum, gebruiker, "Filip Pasmans, zaakvoerder"); handtekening door Filip in Voorvertoning
- Verstuurd 23 okt 16:39 vanaf hallo@kansenradar.be (korte tekst, zonder AV-vraag — keuze Filip).
- FSB technical request-PDF bewust niet gestuurd (vraagt vaste IP's).
- Gmail "verzenden als" hallo@kansenradar.be ingesteld; api@kansenradar.be = forwarder naar Gmail.

## Learnings
- mijn.host-mail: `mx1/mx2.mijn.host` = enkel inkomend (spamfilter), SMTP-login daar faalt. Verzenden: `mail.kansenradar.be` (= h58.mijn.host) poort 587 TLS.
- Een forwarder heeft geen wachtwoord: om vanaf een adres te verzenden is een echte mailbox nodig (mag naast de forwarder bestaan).
- Mails naar overheid/tickets: vanaf het zakelijke adres waar het dossier op loopt, niet vanaf Gmail.
- BOSA-PDF's hebben geen formuliervelden: invullen = tekst op de pagina stempelen (pypdf + reportlab via `uv run --no-project --with ...`).
- Geen Word/LibreOffice op de Mac: .docx-invullen enkel via python-docx en waarden controleren, niet visueel.
- Filip wil geen agendaherinnering voor BOSA-opvolging.

## Geen correcties door Filip deze sessie
(eigen fout: eerst mx1.mijn.host als SMTP voorgesteld → verificatiefout; zelf rechtgezet)

## Open
- Wachten op BOSA (Media-account credentials). Dan: e-Procurement-scraper bouwen.
- Vóór eerste digest met e-Procurement-data: BOSA schriftelijk laten bevestigen dat samenvatten + doorsturen aan betalende klanten mag (AV art. 8 + 11) en dat "e-Procurement" als bron genoemd mag worden (art. 6). Contactgegevens aanbesteders niet in digest.
- Als BOSA toch vaste IP's eist: GitHub Actions heeft die niet → oplossing nodig (bv. self-hosted runner/proxy).
- PDF's in projectroot (o.a. ondertekende overeenkomst) niet committen.

## 29 okt 2026 — credentials ontvangen, INT-test OK
- BOSA (Maxence Fatrez) stuurde `Kansenradar - FSB credentials.docx`: client-ID + secret voor INT én PR (DEMO leeg). PR wordt pas geactiveerd na onze bevestiging dat INT werkt.
- Credentials staan in `.env` (chmod 600) als `EPROC_INT_*` en `EPROC_PR_*` (TOKEN_URL, CLIENT_ID, CLIENT_SECRET). Docx staat in .gitignore.
- Werkende aanroep:
  - Token: POST `{TOKEN_URL}` form `grant_type=client_credentials&client_id=…&client_secret=…` → access_token, 3600 s, scope BOSA.
  - Zoeken: GET `https://public.int.fedservices.be/api/eProcurementSea/v1/search/publications?page=1&pageSize=N&cpvCodes=79340000` met `Authorization: Bearer`, **verplichte header `BelGov-Trace-Id` (uuid4)**, `Accept-Language: nl`. PR-host: `public.fedservices.be` (vermoedelijk, nog te bevestigen).
  - Antwoord: `{publications: [...], totalCount}`; velden o.a. cpvMainCode, cpvAdditionalCodes, dossier, organisation, lots, nutsCodes, publicationDate, publicationType, noticeSubType, referenceNumber, publicationReferenceNumbersTED, tedPublished, procedureId.
- INT = testdata (1 hit op 79340000), dus inhoud niet representatief.
- 29 okt 16:35: Filip mailde BOSA dat INT werkt + vroeg PR-activering. Bewust GEEN vraag over herverdeling (keuze Filip): wel geen persoonsgegevens in digest + meteen bijsturen als BOSA iets vraagt.
- Volgende stap: wachten op PR-activering; daarna scraper `scraper/e_procurement.py` (dedupe met TED via publicationReferenceNumbersTED).

## 29 okt 2026 — e-Procurement-scraper gebouwd (op INT getest)
- `scraper/e_procurement.py` + `tests/test_e_procurement.py`; gekoppeld in `mailer/run.py` (TED-dubbels weg via `publicationReferenceNumbersTED`; gefaalde bron → digest gaat door, workflow faalt daarna voor alert).
- API-bevindingen: `page` verplicht, pageSize max 100, onbekende params stil genegeerd, `publicationDateFrom/To` werken, `cpvCodes` = exacte match (daarom alles ophalen + lokaal CPV-prefixfilter). Deadline = `vaultSubmissionDeadline`, enkel bij oproepen (subtype 7–24, E3); gunningen/vooraankondigingen overgeslagen.
- Aan: `EPROC_ENV=INT|PR`. Workflow leest `EPROC_ENV` + `EPROC_PR_*` uit GitHub secrets (nu leeg = overgeslagen).
- Live INT-run: 578 publicaties/14 dagen, 8 relevant (testdata), 6 requests.
- **Te verifiëren op PR:** (1) link-formaat `publicprocurement.be/publication-workspaces/{id}/general` klikt door; (2) formaat TED-referenties (dedup); (3) of GitHub Actions-IP's toegelaten zijn.
- Go-live na PR-activering: `EPROC_ENV=PR` lokaal testen → GitHub secrets zetten (Filip) → dry-run.

## 29 okt 2026 (avond) — Supabase was gepauzeerd, eerste echte dry-run
- Supabase free-project was gepauzeerd (NXDOMAIN, vermoedelijk sinds ±20 okt) → wachtlijstformulier gaf "Kan geen verbinding maken". Filip herstartte het om 20:45; na ±5 min weer bruikbaar. Voorstel open: keep-alive tot de wekelijkse run draait.
- Eerste volledige dry-run met echte keys (enkel TED): 7 opgehaald, 7/7 relevant, scores 6–7, 5 in digest. Werkt.
- Gefixt na visuele check: TED-titelprefix ("België – CPV – ") weg; bronregel toont enkel bronnen die echt in de digest zitten; "vandaag" → "deze week". `site/api/sample-digest.html` nog niet hergenereerd/gedeployed.
- Opgemerkt: TED geeft voor sommige opdrachten geen deadline (VSV); buitenlandse opdrachten met uitvoering in BE komen mee (bv. Franse champignoncampagne).
- GitHub-workflow faalt al sinds juli dagelijks: secrets nooit gezet (bekend).
- Keep-alive klaargezet: `ops/supabase_keepalive.sh` + `ops/be.kansenradar.supabase-keepalive.plist` (dagelijks 10:00 + bij login, log `~/Library/Logs/kansenradar-keepalive.log`). Installeren door Filip zelf (auto-mode blokkeert LaunchAgents). **Tijdelijk risico/oplossing:** weghalen zodra de wekelijkse digest in GitHub Actions draait (`launchctl bootout gui/$(id -u)/be.kansenradar.supabase-keepalive` + plist uit ~/Library/LaunchAgents verwijderen).
