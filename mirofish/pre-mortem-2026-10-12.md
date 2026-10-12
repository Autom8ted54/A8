# Pre-mortem Kansenradar-validatie (12 oktober 2026)

Uitgangspunt: het is 30 november 2026 en de validatie is mislukt. Waarom?
Gerangschikt van meest waarschijnlijk naar minst. Nog niets van uitgevoerd; later mee verwerken.

## 1. De lat lag hoger dan koude mail haalt
De beslistabel vraagt 30 inschrijvingen uit 288 adressen, dus ruim 10%. Voor koude mail van een onbekende afzender is dat veel. Een paar procent is realistischer (inschatting, geen gemeten cijfer). Dan "faal" je terwijl het idee misschien wel goed is.
- Vroeg signaal: na de eerste 100 mails nog maar een handvol inschrijvingen.
- Te doen: vóór de start afspreken wat "goed genoeg" is bij 288 adressen. Ook antwoorden en gesprekken meetellen, niet alleen inschrijvingen.

## 2. Er was te weinig tijd
Bij opwarmen van 10 naar 40 mails per dag duren alleen de eerste mails al ongeveer twee weken. Opvolging komt op dag 4 en dag 10. Bij een start begin november komen de laatste antwoorden pas rond het beslismoment eind november binnen. Het verzendscript bestaat nog niet.
- Te doen: het script bouwen, of het beslismoment naar half december verschuiven.

## 3. De mails kwamen in de spam
kansenradar.eu is een nieuw domein en de afzender is onbekend. SPF, DKIM en DMARC staan goed, maar dat garandeert niets.
- Vroeg signaal: bounces, nul antwoorden, ook geen "stop".
- Te doen: testen met mail-tester.com en naar een paar eigen adressen bij Gmail en Outlook sturen vóór golf A vertrekt.

## 4. De ervaren bureaus prikten erdoor
De 84 winnaars in golf A kennen de markt. Kleinere Vlaamse opdrachten staan alleen op e-Procurement; nu is er enkel de Europese bron TED. De voorbeeldmail toont dus vooral grote opdrachten. Hun reactie: "dat zien wij zelf ook".
- Te doen: de API-sleutel voor e-Procurement (BOSA) tijdig aanvragen, want dat duurt even.

## 5. De site beloofde wat er niet was
Filteren op regio, alerts, een menselijke check en subsidies bestaan nog niet. De voorbeeldmail op de site toont verzonnen opdrachten, de bedankmail echte. Eén scherpe vraag zoals "hoe filteren jullie op mijn regio?" en de geloofwaardigheid wankelt.
- Te doen: vóór de outreach beslissen over de 4 beloftes: schrappen, "binnenkort" erbij zetten, of bouwen.

## 6. Wel inschrijvingen, maar niemand betaalt
De wachtlijst is gratis en zonder creditcard. 30 inschrijvingen zeggen dus weinig over betalen. Dan "slaag" je op papier en faal je pas bij de lancering.
- Te doen: in het persoonlijke contact iets concreets vragen, bijvoorbeeld "mag ik je de eerste factuur sturen als we in januari starten?". Enkel de ja's tellen als echt signaal.

## 7. Juridisch gedoe met koude mail
Voor zover bekend mag je in België ongevraagd mailen naar algemene bedrijfsadressen (zoals info@), maar niet zomaar naar persoonlijke adressen (zoals jan@bureau.be). Eén klacht kost reputatie in een kleine sector. Zelf nog nachecken, dit is geen juridisch advies.
- Te doen: nakijken hoeveel van de 288 adressen persoonlijk zijn.

## 8. Kleinere oorzaken
Maken het moeilijker, maar doen het waarschijnlijk niet alleen mislukken:
- Bureaus zitten eind november in hun eindejaarsdrukte.
- De reactie "dat bouw ik zelf met AI".
- De site oogt generiek; de design-refresh staat nog open.

## Voorgestelde volgorde
1. Het verzendscript bouwen en testen op spam (punten 2 en 3).
2. Beslissen over de 4 beloftes op de site (punt 5).
3. De e-Procurement-sleutel aanvragen (punt 4).
