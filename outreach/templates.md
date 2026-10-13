# Outreachmails Kansenradar (concept, ter goedkeuring)

Afzender: Filip <OUTREACH_EMAIL> (kansenradar.eu), zonder aparte Reply-To: antwoorden komen in de outreachmailbox, zodat het script "stop" en antwoorden automatisch herkent.
Verzenden: `uv run python -m outreach.send` (zie de uitleg bovenaan `outreach/send.py`).
Lichte opmaak: elke mail gaat als platte tekst + eenvoudige HTML-versie (klein logo en link in de signatuur, voorbeeldopdracht als kader). Geteste plaats: Gmail Primair.
`{voorbeeld}` = één echte, nog openstaande opdracht, automatisch gekozen uit `mailer/sample_tenders.json` (hoogste score, deadline minstens 7 dagen weg). Is er geen geschikte meer, dan weigert het script te versturen.
Mail 2 en 3 gaan als antwoord in dezelfde conversatie en stoppen automatisch zodra iemand antwoordt.
`{naam}` = bedrijfsnaam. De link bevat `?bron=…` zodat we zien welke mail werkt.

---

## Golf A: bureaus die al overheidsopdrachten wonnen

### Mail A1 (dag 0)
**Onderwerp:** Overheidsopdrachten voor {naam}

Beste,

Ik zag dat {naam} de voorbije jaren al overheidsopdrachten binnenhaalde. Dan weet je ook hoeveel tijd het kost om ze op tijd te vinden.

Daarvoor bouwen we Kansenradar: wij monitoren de Belgische en Europese publicaties, en jij krijgt elke maandag één mail met enkel de opdrachten voor marketing- en communicatiebureaus. Kort samengevat, zodat je in twee minuten weet of het iets voor jullie is. Wij monitoren, jij beslist.

Een voorbeeld dat nu openstaat:

{voorbeeld}

We starten binnenkort met 50 founding members. Inschrijven op de wachtlijst is gratis, en je krijgt meteen een voorbeeld met echte opdrachten:
https://kansenradar.be/?bron=a1

Groeten,
Filip
Kansenradar, een initiatief van Autom8ted

Geen interesse? Antwoord "stop" en je hoort niets meer van ons.

### Mail A2 (dag 4, antwoord op A1)
**Onderwerp:** Re: Overheidsopdrachten voor {naam}

Beste,

Even een korte opvolging. Hoe volgen jullie vandaag de nieuwe opdrachten op? Zelf zoeken, via een tool, of eerder als iemand je er toevallig op wijst?

Als het je tijd zou besparen: op de wachtlijst zie je meteen hoe zo'n wekelijkse mail eruitziet.
https://kansenradar.be/?bron=a2

Groeten,
Filip

### Mail A3 (dag 10, antwoord op A1)
**Onderwerp:** Re: Overheidsopdrachten voor {naam}

Beste,

Ik stuur je hierover geen mails meer. Mocht het later toch interessant worden: de founding member-plaatsen (het eerste jaar €29/maand in plaats van €59) staan nog open zolang ze niet vol zijn.
https://kansenradar.be/?bron=a3

Veel succes met de volgende opdracht,
Filip

---

## Golf B: overige marketing- en communicatiebureaus

### Mail B1 (dag 0)
**Onderwerp:** Overheidsopdrachten voor {naam}?

Beste,

Elke week publiceren Vlaamse overheden nieuwe opdrachten voor communicatie, marketing, events en websites. De meeste bureaus zien ze nooit, of pas als de deadline bijna voorbij is.

Met Kansenradar monitoren wij alle publicaties, en jij krijgt elke maandag één mail met enkel wat relevant is voor een bureau zoals {naam}, kort samengevat. Wij monitoren, jij beslist.

Zo staat er nu bijvoorbeeld dit open:

{voorbeeld}

We starten binnenkort met 50 founding members. Inschrijven op de wachtlijst is gratis, en je krijgt meteen een voorbeeld met echte opdrachten:
https://kansenradar.be/?bron=b1

Groeten,
Filip
Kansenradar, een initiatief van Autom8ted

Geen interesse? Antwoord "stop" en je hoort niets meer van ons.

### Mail B2 (dag 4) en B3 (dag 10)
Dezelfde tekst als A2 en A3, met de links `?bron=b2` en `?bron=b3`.

---

## Standaardantwoorden (voor jou, om te kopiëren)

**"Wat kost het?"**
Founding members betalen de eerste 12 maanden €29 per maand, daarna €59 (excl. btw). Maandelijks opzegbaar, geen jaarcontract. Alle voorwaarden: https://kansenradar.be/voorwaarden.html Op de wachtlijst betaal je niets: we contacteren je persoonlijk voor de lancering, en pas dan beslis je.

**"Hoe werkt het precies?"**
Wij volgen doorlopend de Belgische en Europese publicaties van overheidsopdrachten op. We filteren op opdrachten voor marketing- en communicatiebureaus en vatten elke opdracht kort samen: wat er gevraagd wordt, het budget als dat bekend is, en de deadline. Elke maandag krijg je één mail. Geen platform, geen login.

**Factuurvraag (bij wie interesse toont: dit is het "harde ja" voor de beslistabel)**
Fijn om te horen. Mag ik je de eerste factuur sturen zodra we starten? Dat is €29 per maand excl. btw, maandelijks opzegbaar, en het abonnement loopt pas vanaf je eerste digest. Een kort "ja" volstaat; ik neem dan contact op vóór de eerste maandag.

**"Wanneer start het?"**
We starten met de eerste founding members zodra de wachtlijst vol genoeg is. Wie op de lijst staat, contacteren we persoonlijk en hoort het als eerste.

**"Geen interesse" / "stop"**
Helemaal goed, bedankt om het te laten weten. Je ontvangt geen mails meer van ons.
(Het script haalt dit adres automatisch van de lijst.)
