# 2026-10-12/13 — MiroFish-seed, pre-mortem, plan v2, outreach-test, design-refresh

## Gedaan
- MiroFish-seed (`mirofish/launch-seed.txt`), pre-mortem en klantsimulatie (2 kopen / 4 misschien / 6 nee) in `mirofish/`.
- Plan v2 (vervangt v1; backup ernaast): geen outreach vóór e-Procurement in de digest zit, beslismoment schuift mee. Beslissingen 1-per-1 met Filip.
- Site: eerlijke bronnenclaim, excl. btw, FAQ, voorwaardenpagina, bedrijfsgegevens. Live.
- BOSA-aanvraag e-Notification-API verstuurd (13 okt) naar e.proc@publicprocurement.be.
- `outreach/send.py`: opwarmen, opvolging in thread, stop/antwoord/bounce via IMAP, echte openstaande opdracht in mail 1, lichte HTML + logo. Gmail Primair, mail-tester 9,5/10. Niets naar bureaus verstuurd.
- Outreachmailbox hallo@kansenradar.eu in Mail op de Mac (via .mobileconfig, wachtwoord door Filip).
- Design-refresh: 3 varianten, Filip koos B "Radar". Live op site, voorwaarden en mails. Backup-tag `pre-design-refresh-2026-10-13`.
- Gedetailleerde voortgang: `2026-10-13-plan-v2-uitvoering.md`.

## Learnings
- Vragen 1-per-1 (bestaande regel, opnieuw gevraagd): ook beslispunten uit een plan niet bundelen; stel ze één voor één vóór je het plan afrondt.
- Werkwijze bij uitvoering: eerst alles doen wat Claude zelf kan, dan Filips stappen één voor één op prioriteit, voortgang opslaan na elke belangrijke stap (eerste keer gevraagd).
- Filip vraagt "kan jij dit doen?" bij handmatige stappen (mail-tester, Mail-account): eerst zelf proberen (browser, profielbestand) vóór je een stap teruggeeft (eerste keer).
- Koude mail in platte tekst vond Filip te saai: lichte HTML + logo landde nog steeds in Primair (eerste keer).
- Deploy (`./deploy.sh`) wordt door de auto-mode-classifier geblokkeerd: Filip draait `! ./deploy.sh` zelf.
- Wachtwoorden nooit zelf invullen: account-setup via een configuratieprofiel zonder wachtwoord werkt goed.
- TenderWolf (gecheckt 13 okt): Free €0, Standard €79, Professional €149; geen gezichten, wel klantlogo's.

## Bewust genomen risico's (zie plan)
- Koude mail naar persoonlijke adressen: tot eerste klacht of na golf B herbekijken.
- Vergelijkingstabel zonder gratis plan TenderWolf: herbekijken bij vraag van een bureau of bij lancering.

## Open
- Antwoord BOSA afwachten; opvolgen rond 20 okt (02 740 80 00).
- Daarna: e-Procurement-scraper + zoekwoorden voor events onder "logistiek" (belofte in FAQ), voorbeeldmail vernieuwen, go golf A.
- Herinnering 20 okt in Google Agenda: aangeboden, nog niet bevestigd.
