# Kansenradar — Projectcontext voor Claude Code

## Wat is Kansenradar?
Een Belgische B2B intelligence service die marketing- en communicatiebureaus wekelijks op de hoogte houdt van relevante overheidsopdrachten. Geen platform, geen dashboard in fase 1 — het product is een curated wekelijkse e-maildigest (maandag 07:00).

Mentale referentie voor de eindgebruiker: **Buienradar** — vertrouwd, functioneel, no-nonsense.

## Positionering — Messaging Regels
- **ALTIJD zeggen:** "intelligence service", "wij monitoren — jij beslist", "voor marketing- en communicatiebureaus"
- **NOOIT zeggen:** "AI-tool", "platform", "revolutionair", "game-changer", "dataplatform"
- Tone of voice: direct Vlaams Nederlands (je/jij, nooit u), zelfzeker maar niet arrogant, altijd concreet

## Tech Stack
| Laag | Technologie | Kost |
|------|-------------|------|
| Scrapers | Python 3.11+ | gratis |
| Databronnen | e-Procurement BE (e-notification.be), TED (ted.europa.eu) | gratis |
| AI verwerking | Claude API — Haiku (pre-screening) + Sonnet (samenvatting) | < €5/mnd |
| Database | Supabase PostgreSQL (free tier) | gratis |
| E-mail bezorging | Resend (free tier, <100/dag) | gratis |
| Landingspagina | Statische HTML/CSS/JS + PHP-endpoint op mijn.host (deploy.sh via FTP) | hosting |
| Orchestratie | GitHub Actions (dagelijkse cron) | gratis |
| Betaling | Mollie (geen maandkost, enkel transactie %) | variabel |
| DNS | mijn.host (kansenradar.be site/mail, kansenradar.eu outreach) | hosting |

### AI verwerkingsstrategie
1. **CPV-filter** — Python logica (geen AI, gratis)
2. **Haiku** — pre-screening: relevant ja/nee per tender
3. **Sonnet** — alleen voor tenders die filter halen: samenvatting + eindscore

## Projectstructuur
```
kansenradar/
├── CLAUDE.md                    ← dit bestand
├── .gitignore
├── deploy.sh                    ← upload site/ naar mijn.host (leest .env, genereert api/config.php)
├── site/                        ← webroot op mijn.host
│   ├── index.html               ← wachtlijstpagina
│   ├── css/style.css
│   ├── js/main.js
│   ├── assets/                  ← favicon, OG image
│   └── api/
│       ├── waitlist.php         ← inschrijving → Supabase + Resend-bedankmail
│       └── sample-digest.html   ← gegenereerd door `uv run python -m mailer.build_sample`
├── supabase/
│   └── migrations/
│       └── 001…004_*.sql        ← handmatig via Supabase SQL-editor
├── outreach/                    ← prospectlijst (state/ = gitignored) + templates.md
├── .github/
│   └── workflows/
│       ├── daily-digest.yml     ← GitHub Actions cron (maandag 06:00 UTC)
│       └── supabase-keepalive.yml ← dagelijkse ping, voorkomt pauze free tier
├── scraper/                     ← Python data ingestion
│   ├── base.py                  ← Source-interface
│   ├── ted_europa.py            ← TED API v3
│   └── e_procurement.py         ← BOSA eProcurementSea-API (EPROC_ENV=INT|PR)
├── processor/                   ← AI verwerking
│   ├── cpv_filter.py            ← prefix-match, geen AI
│   ├── prescreen.py             ← Haiku ja/nee
│   └── summarizer.py            ← Sonnet samenvatting + score
├── database/                    ← Supabase client + models
│   ├── client.py
│   └── models.py
├── tests/                       ← pytest (uv run pytest)
└── mailer/                      ← e-mail digest pipeline
    ├── run.py                   ← orchestratie volledige pipeline (--dry-run)
    ├── digest_builder.py
    ├── sender.py
    └── templates/
        └── digest.html
```

## Omgevingsvariabelen (nooit in code)
```
ANTHROPIC_API_KEY=            # Claude API
SUPABASE_URL=                 # https://<project>.supabase.co
SUPABASE_ANON_KEY=            # Publieke sleutel (alleen voor client-side)
SUPABASE_SERVICE_KEY=         # Service role (server-side only, bypasses RLS)
RESEND_API_KEY=               # E-mail bezorging
FROM_EMAIL=digest@kansenradar.be
EPROC_ENV=                    # INT | PR (leeg = e-Procurement overgeslagen)
EPROC_<ENV>_TOKEN_URL=        # + EPROC_<ENV>_CLIENT_ID / _CLIENT_SECRET (BOSA FSB)
DIGEST_SEND_TIME=07:00        # Dagelijkse verzendtijd
MAX_TENDERS_PER_DIGEST=5
MIN_RELEVANCE_SCORE=6
```

## Sleutelterminologie
- **CPV-codes:** Common Procurement Vocabulary — EU-classificatie voor overheidsopdrachten
  - 79340000 Reclame- en marketingdiensten
  - 79341000 Reclamediensten
  - 79342000 Marketingdiensten
  - 79416000 Public relationsdiensten
  - 79952000 Evenementendiensten
  - 72413000 Websiteontwerpdiensten
- **e-Procurement / e-Notification:** Belgisch federaal aankoopplatform
- **TED:** Tenders Electronic Daily — EU-breed publicatieplatform voor overheidsopdrachten
- **Overheidsopdracht:** Government tender / public procurement
- **Bestek:** Aanbestedingsdocument met technische specificaties
- **Founding member:** Eerste 50 klanten aan gereduceerd tarief (€29/mnd gedurende de eerste 12 maanden, daarna €59)
- **NUTS-regio BE:** Geografische filtercode voor België/Vlaanderen

## Conventies
- Landingspagina: vanilla HTML/CSS/JS, geen build-stap, geen framework
- Python: PEP8, type hints, logging via `logging` module
- Alle secrets via environment variables, **nooit** in code of git
- Kopij (user-facing): altijd Nederlands (Vlaams)
- Code, commentaar, commit messages: Engels

## Outreach & validatie
- Outreachmails openen met "Beste,"; vertrekken vanaf kansenradar.eu (eigen SMTP-script), nooit vanaf kansenradar.be en niet via Brevo (verbiedt koude lijsten)
- LinkedIn: enkel de bedrijfspagina, nooit Filips persoonlijke profiel
- Prijs- of frequentiewijziging ook doorvoeren in `outreach/templates.md` (A3 + standaardantwoorden) en `mailer/build_sample.py`
- Beslistabel validatie: nooit automatisch stoppen of bijsturen — altijd eerst samen met Filip beslissen
- Testinschrijvingen hebben source=test; uitsluiten uit cijfers
- Bronnenclaim volgt de echte bronnen: zolang alleen TED draait, nergens "alle publieke aanbestedingen" beloven of doen alsof Belgische publicaties er al in zitten. Geen outreach vóór e-Procurement in de digest zit (beslist 13 okt 2026)

## Pricing
Alle prijzen excl. btw (Autom8ted, BTW BE 1037.472.507). Voorwaarden: `site/voorwaarden.html`.

| Plan | Prijs | Doelgroep |
|------|-------|-----------|
| Founding Member | €29/mnd | Eerste 50 klanten, 12 maanden (site toont €59 doorstreept) |
| Starter | €59/mnd | Standaard na launch en na de founding-periode |
| Pro | (later) | Meerdere gebruikers + filters |

## Fase 1 Mijlpalen
- Week 1–6: Validatie via outreach + wachtlijst (landingspagina)
- Week 6–8: 30+ founding members → start bouwen
- Week 8–12: Scraper + AI processor + eerste digest
- Maand 4+: Dashboard, subsidies, verfijning

## Succesindicatoren Fase 1
- 30–50 founding members
- MRR €870–€1.450
- Open rate digest >50%
- Gemiddelde relevantiescore >7/10
