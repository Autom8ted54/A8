# Kansenradar — Projectcontext voor Claude Code

## Wat is Kansenradar?
Een Belgische B2B intelligence service die marketing- en communicatiebureaus dagelijks op de hoogte houdt van relevante overheidsopdrachten. Geen platform, geen dashboard in fase 1 — het product is een curated dagelijkse e-maildigest.

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
| Landingspagina | Statische HTML/CSS/JS op Cloudflare Pages | gratis |
| Orchestratie | GitHub Actions (dagelijkse cron) | gratis |
| Betaling | Mollie (geen maandkost, enkel transactie %) | variabel |
| DNS / CDN | Cloudflare | gratis |

### AI verwerkingsstrategie
1. **CPV-filter** — Python logica (geen AI, gratis)
2. **Haiku** — pre-screening: relevant ja/nee per tender
3. **Sonnet** — alleen voor tenders die filter halen: samenvatting + eindscore

## Projectstructuur
```
kansenradar/
├── CLAUDE.md                    ← dit bestand
├── .gitignore
├── site/                        ← Cloudflare Pages (publish directory)
│   ├── index.html               ← wachtlijstpagina
│   ├── css/style.css
│   ├── js/main.js
│   ├── assets/                  ← favicon, OG image
│   └── functions/api/
│       └── waitlist.js          ← Cloudflare Pages Function → Supabase
├── supabase/
│   └── migrations/
│       └── 001_create_waitlist.sql
├── .github/
│   └── workflows/
│       └── daily-digest.yml     ← GitHub Actions cron (weekdagen 06:00 UTC)
├── scraper/                     ← (fase 2) Python data ingestion
│   ├── e_notification.py
│   └── ted_europa.py
├── processor/                   ← (fase 2) AI verwerking
│   ├── summarizer.py
│   ├── scorer.py
│   └── cpv_filter.py
├── database/                    ← (fase 2) Supabase client + helpers
│   └── client.py
└── mailer/                      ← (fase 2) e-mail digest pipeline
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
E_NOTIFICATION_API_KEY=       # e-Procurement API
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
- **Founding member:** Eerste 50 klanten aan gereduceerd tarief (€39/mnd)
- **NUTS-regio BE:** Geografische filtercode voor België/Vlaanderen

## Conventies
- Landingspagina: vanilla HTML/CSS/JS, geen build-stap, geen framework
- Python: PEP8, type hints, logging via `logging` module
- Alle secrets via environment variables, **nooit** in code of git
- Kopij (user-facing): altijd Nederlands (Vlaams)
- Code, commentaar, commit messages: Engels
- Cloudflare Pages Functions: `export async function onRequestPost(context)` patroon, env via `context.env`

## Pricing
| Plan | Prijs | Doelgroep |
|------|-------|-----------|
| Founding Member | €39/mnd | Eerste 50 klanten |
| Starter | €49/mnd | Standaard na launch |
| Pro | €89/mnd | Meerdere gebruikers + filters |

## Fase 1 Mijlpalen
- Week 1–6: Validatie via outreach + wachtlijst (landingspagina)
- Week 6–8: 30+ founding members → start bouwen
- Week 8–12: Scraper + AI processor + eerste digest
- Maand 4+: Dashboard, subsidies, verfijning

## Succesindicatoren Fase 1
- 30–50 founding members
- MRR €1.170–€1.950
- Open rate digest >50%
- Gemiddelde relevantiescore >7/10
