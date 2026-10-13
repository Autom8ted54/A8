# 2026-10-13 — Uitvoering plan v2 (na pre-mortem + simulatie)

Plan: `~/.claude/plans/ik-heb-hier-niets-vivid-backus.md` (v2; v1-backup ernaast).
Werkwijze: eerst alles wat Claude zelf kan, dan Filips vragen/stappen ÉÉN VOOR ÉÉN op prioriteit. Na elke belangrijke stap dit bestand bijwerken.

## Klaar (Claude)
- [x] Plan v2 geschreven en in de plek van v1 gezet (backup `ik-heb-hier-niets-vivid-backus.v1-backup-2026-10-13.md`)
- [x] Site-teksten (lokaal, NIET gedeployed): eerlijke bronnenclaim, excl. btw, alerts "binnenkort", FAQ (6 vragen), bedrijfsgegevens in footer (Autom8ted, Mortsel, KBO/BTW 1037.472.507). Backup: `backup/index.pre-plan-v2-2026-10-13.html`
- [x] `site/voorwaarden.html` (v1.0) — wacht op goedkeuring Filip
- [x] Visuele check lokaal desktop + mobiel (iframe-wrapper) ok
- [x] `outreach/templates.md`: "Wat kost het?" excl. btw + link voorwaarden; nieuwe "factuurvraag" (= harde ja)
- [x] CLAUDE.md: excl. btw + regel bronnenclaim / geen outreach vóór e-Procurement
- [x] BOSA: geen publieke API-procedure gevonden (ook niet in juli). Route = helpdesk e.proc@publicprocurement.be. Aanvraagmail klaar in `admin/bosa-api-aanvraag.txt`

- [x] Outreach-verzendscript `outreach/send.py` (+ 13 tests, alle 58 tests groen): teksten uit templates.md, opwarmen 10→40/dag (+2/dag), opvolging dag 4/10 in dezelfde thread, stop/antwoord/bounce via IMAP (ook Outlook-quotes), alleen weekdagen, state na elke mail. SMTP- en IMAP-login op kansenradar.eu getest, NIETS verstuurd. Geen Reply-To meer: antwoorden komen in de outreachmailbox (nodig voor stopdetectie)

## Bezig / volgt (Claude)
- [ ] Na goedkeuring: deploy + live check
- [ ] e-Procurement-scraper zodra toegang er is (+ events onder "logistiek" via zoekwoorden: belofte in FAQ)

## Wachtrij vragen/stappen voor Filip (één per één, in deze volgorde)
1. Voorwaardenpagina + FAQ goedkeuren (bevatten beleid: doorsturen mag, PO op factuur, opzeggen einde maand, geen terugbetaling lopende maand, aansprakelijkheid beperkt tot 12 mnd) → daarna deploy
2. BOSA-mail versturen (tekst in `admin/bosa-api-aanvraag.txt`, via pbcopy) vanaf hallo@kansenradar.be
3. Testmails: Filip geeft het adres waar 6 testmails (A1-3, B1-3) heen mogen → `uv run python -m outreach.send --test ADRES`; daarna één naar mail-tester.com
4. Outreachmailbox kansenradar.eu laten doorsturen (met kopie bewaren) naar Filips gewone inbox, zodat hij antwoorden ziet
5. Later: go voor golf A zodra e-Procurement in de digest zit

## Beslissingen 13 okt (zie plan)
excl. btw · mix beloftes (regio/sector + menselijke check blijven, Filip ±15 min/week) · alleen bedrijfsgegevens · tabel TenderWolf ongewijzigd (risico genoteerd) · nieuwe meetlat met harde ja's · persoonlijke adressen gewoon versturen (risico genoteerd) · geen extra garantie · alle outreach wacht op e-Procurement, beslismoment ±4 weken na eerste mail
