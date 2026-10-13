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

- [x] Voorwaarden + FAQ goedgekeurd door Filip; LIVE gezet 13 okt 09:5x (deploy.sh door Filip zelf: auto-mode classifier blokkeert deploy door Claude). Live check desktop + mobiel ok

- [x] Test 1 (13 okt 10:36): platte tekst landt in Gmail Primair. Filip vond hem saai → keuze 'Beide': echte openstaande opdracht in mail 1 (auto uit mailer/sample_tenders.json, ≥7 dagen open, anders weigert script) + lichte HTML (kaartje, logo-signatuur `site/assets/logo-mail.png`). Logo gedeployed; test 2 (10:42): Gmail Primair, Filip: 'ziet er goed uit' ✓. mail-tester (13 okt 10:44): 9.5/10 (SPF/DKIM/DMARC pass; enige aftrek 0.5 voor kleine HTML met afbeelding) ✓

## Bezig / volgt (Claude)
- [ ] e-Procurement-scraper zodra toegang er is (+ events onder "logistiek" via zoekwoorden: belofte in FAQ)

## Wachtrij vragen/stappen voor Filip (één per één, in deze volgorde)
1. ~~Voorwaarden + FAQ goedkeuren~~ ✓
2. ~~BOSA-mail versturen~~ ✓ verstuurd 13 okt 10:35 naar e.proc@publicprocurement.be. Wachten op antwoord; geen reactie tegen ±20 okt → opvolgen (helpdesk ook telefonisch 02 740 80 00)
3. ~~Testmails + mail-tester~~ ✓ — 6 verstuurd 13 okt 10:36 naar Filips Gmail (state onaangeroerd) — wacht op zijn bevinding (inbox/spam, opmaak). Daarna mail-tester. Origineel: Filip geeft het adres waar 6 testmails (A1-3, B1-3) heen mogen → `uv run python -m outreach.send --test ADRES`; daarna één naar mail-tester.com
4. ~~Outreachmailbox in Mail op de Mac~~ ✓ 13 okt 10:48 (via .mobileconfig-profiel, wachtwoord door Filip zelf; verwijderen = profiel weg in Systeeminstellingen)
5. Later: go voor golf A zodra e-Procurement in de digest zit

## Beslissingen 13 okt (zie plan)
excl. btw · mix beloftes (regio/sector + menselijke check blijven, Filip ±15 min/week) · alleen bedrijfsgegevens · tabel TenderWolf ongewijzigd (risico genoteerd) · nieuwe meetlat met harde ja's · persoonlijke adressen gewoon versturen (risico genoteerd) · geen extra garantie · alle outreach wacht op e-Procurement, beslismoment ±4 weken na eerste mail

## Stand 13 okt 10:48
Alle voorbereiding klaar. Alles wacht nu op het antwoord van BOSA (e-Procurement-toegang).
Volgende zodra BOSA antwoordt: scraper bouwen (stap 6 plan), voorbeeldmail vernieuwen (7), go golf A (9).
Opvolgen BOSA rond 20 okt als er niets komt. In de wachttijd mogelijk: design-/fontrefresh (niet blokkerend).

## Design-refresh (gestart 13 okt 10:51)
- Backup: `backup/pre-design-refresh-2026-10-13/` + git-tag `pre-design-refresh-2026-10-13`
- 3 varianten in `design-varianten/` (build.py genereert uit site/index.html; content identiek): A Maandagbrief (Literata, luchtpost-envelop + draaiend poststempel), B Radar (Bricolage Grotesque + Instrument Sans, radar met oplichtende opdrachten), C Weerbericht (Young Serif + Figtree, wolken + weekvoorspelling ma 07:00)
- Bekijken: `python3 -m http.server 8766` in projectroot → localhost:8766/design-varianten/variant-a.html
- Filip koos B (Radar) 10:56. Uitgewerkt: theme `.theme-radar` onderaan style.css, radar-markup in index.html, fonts Bricolage Grotesque + Instrument Sans op index + voorwaarden; mails: navy #0E2340, Instrument Sans/Bricolage in digest + outreach-HTML, sample-digest herbouwd. Visueel gecheckt desktop + mobiel. LIVE 13 okt ±11:00, live gecheckt desktop + mobiel ✓. Design-refresh AFGEROND.
