# 2026-10-10 — Validatie: wachtlijst live, outreachvoorbereiding, prijs

## Gedaan
- Validatieplan opgesteld en goedgekeurd (wachtlijst + outreach vóór verder bouwen; beslismoment eind november, altijd samen).
- Site live op https://kansenradar.be (mijn.host, deploy.sh via FTP), formulier → PHP → Supabase → Resend-bedankmail met voorbeeld-digest. End-to-end getest (gsm, mobiele data).
- Interessevraag zonder koopgevoel, `?bron=`-tracking, contactadres hallo@kansenradar.be.
- Outreachdomein kansenradar.eu (SPF/DKIM/DMARC ok). Prospectlijst: 288 geverifieerde adressen (golf A: 84 TED-winnaars, golf B: 204).
- Outreachteksten in outreach/templates.md (openen met "Beste,").
- Prijs en frequentie beslist: wekelijkse digest (maandag 7:00), founding €29/mnd eerste 12 maanden, daarna €59. Live gezet.
- Design-/fontrefresh ingepland (Google Calendar 12 okt 14u).

## Learnings
- Filip wil vragen één per één, niet in een bundel.
- Outreachmails openen met "Beste", niet "Hoi".
- Geen persoonlijk LinkedIn — enkel de bedrijfspagina.
- Stoppen/bijsturen nooit automatisch op basis van de beslistabel: altijd eerst overleggen.
- Brevo verbiedt koude lijsten → eigen SMTP/IMAP-script vanaf kansenradar.eu.
- mijn.host-botchallenge blokkeert curl/extensie na veel requests; echte bezoekers passeren. Testen via gsm op mobiele data.
- Prijs is geen verdediging tegen "zelf met AI zoeken"; volledigheid (e-Procurement), regelmaat en selectie wel.
- Credentials van andere projecten niet gebruiken; Filip zet eigen gegevens in .env.

## Open
- Outreach-verzendscript bouwen (opwarmen 10→40/dag, opvolging dag 4 en 10, stop bij antwoord, bounces) + test naar eigen adres en mail-tester.com.
- Beslissing over de 4 site-beloftes: menselijke check, sector/regio-filter, deadline/budgetalerts, subsidies.
- BOSA API-sleutel e-Procurement aanvragen (maakt de digest voller).
- LinkedIn-bedrijfsposts schrijven.
- Design-/fontrefresh (12 okt).
- Productie-digest (cron + template) nog op "dagelijks/vandaag" — aanpassen wanneer de echte digest gebouwd wordt.
