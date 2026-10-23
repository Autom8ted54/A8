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
