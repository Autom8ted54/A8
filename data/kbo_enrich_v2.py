import pandas as pd
import re
import time
import requests
from urllib.parse import urlparse, urljoin
from duckduckgo_search import DDGS

OUT_DIR = '/Users/NomadFilip/Documents/kansenradar/output'
INPUT   = f'{OUT_DIR}/kansenradar_top_prospects_verrijkt.csv'
OUTPUT  = f'{OUT_DIR}/kansenradar_top_prospects_verrijkt.csv'

EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
BLACKLIST_LOCAL  = {'noreply','no-reply','mailer-daemon','postmaster','bounce',
                    'donotreply','privacy','gdpr','support','admin','webmaster'}
BLACKLIST_DOMAIN = {'sentry.io','wix.com','squarespace.com','wordpress.com',
                    'example.com','schema.org','w3.org'}
SKIP_DOMAINS     = {'facebook.com','linkedin.com','instagram.com','twitter.com',
                    'youtube.com','wikipedia.org','yelp.com','tripadvisor.com',
                    'goudengids.be','zlatestranky.cz','trustedin.com','companyweb.be',
                    'bijlage.be','staatsblad.be','monitor.be'}

HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                         'AppleWebKit/537.36 (KHTML, like Gecko) '
                         'Chrome/120.0.0.0 Safari/537.36'}

def clean_email(email):
    e = email.strip().lower()
    if not e or '@' not in e:
        return None
    local, domain = e.rsplit('@', 1)
    if local in BLACKLIST_LOCAL:
        return None
    if domain in BLACKLIST_DOMAIN:
        return None
    if any(e.endswith(ext) for ext in ('.png','.jpg','.gif','.css','.js','.svg')):
        return None
    if len(local) < 2 or len(domain) < 4:
        return None
    return e

def score_email(email):
    """Lagere score = beter."""
    local = email.split('@')[0]
    if local in ('info','contact','hello','hallo','post','office','mail'):
        return 0
    if re.match(r'^[a-z]+\.[a-z]+$', local):  # voornaam.naam
        return 1
    return 2

def best_email(emails):
    cleaned = [clean_email(e) for e in emails]
    cleaned = [e for e in cleaned if e]
    if not cleaned:
        return None
    return sorted(set(cleaned), key=score_email)[0]

def is_company_site(url, bedrijfsnaam):
    """Controleer of URL waarschijnlijk de bedrijfswebsite is (geen directory)."""
    domain = urlparse(url).netloc.lower().replace('www.', '')
    for skip in SKIP_DOMAINS:
        if skip in domain:
            return False
    return True

def ddg_find_website(naam, gemeente, max_retries=3):
    """Zoek bedrijfswebsite via DuckDuckGo."""
    query = f'"{naam}" {gemeente} contact'
    for attempt in range(max_retries):
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5, region='be-nl'))
            for r in results:
                url = r.get('href', '')
                if url and is_company_site(url, naam):
                    # Normaliseer naar root domain
                    parsed = urlparse(url)
                    root = f"{parsed.scheme}://{parsed.netloc}"
                    return root
            return None
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(3 + attempt * 2)
            else:
                return None

def scrape_emails_from_url(url, timeout=8):
    """Haal emails op van een URL."""
    try:
        r = requests.get(url, timeout=timeout, headers=HEADERS, allow_redirects=True)
        if r.status_code != 200:
            return []
        # Decode obfuscated atob() emails
        text = r.text
        atob_matches = re.findall(r'atob\(["\']([A-Za-z0-9+/=]+)["\']\)', text)
        for b64 in atob_matches:
            try:
                import base64
                decoded = base64.b64decode(b64).decode('utf-8', errors='ignore')
                text += ' ' + decoded
            except Exception:
                pass
        return EMAIL_RE.findall(text)
    except Exception:
        return []

def find_contact_page(base_url, homepage_html):
    """Vind link naar contactpagina."""
    contact_patterns = re.compile(
        r'href=["\']([^"\']*(?:contact|over-ons|overons|team|about|bereik|'
        r'contacteer|contactez|nous-contacter|adres)[^"\']*)["\']',
        re.IGNORECASE
    )
    matches = contact_patterns.findall(homepage_html)
    for match in matches[:3]:
        if match.startswith('http'):
            return match
        return urljoin(base_url, match)
    return None

def get_email_from_website(website_url):
    """Volledig scrape-proces: homepage + contactpagina."""
    try:
        r = requests.get(website_url, timeout=8, headers=HEADERS, allow_redirects=True)
        if r.status_code != 200:
            return None
        homepage_html = r.text
        emails = EMAIL_RE.findall(homepage_html)

        # Contactpagina
        contact_url = find_contact_page(website_url, homepage_html)
        if contact_url and contact_url != website_url:
            contact_emails = scrape_emails_from_url(contact_url)
            emails.extend(contact_emails)

        return best_email(emails)
    except Exception:
        return None

def goudengids_search(naam, gemeente):
    """Zoek via Gouden Gids als fallback."""
    query = f'site:goudengids.be "{naam}" {gemeente}'
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3, region='be-nl'))
        for r in results:
            url = r.get('href', '')
            if 'goudengids.be' in url:
                emails = scrape_emails_from_url(url)
                e = best_email(emails)
                if e:
                    return e
        return None
    except Exception:
        return None

# ─── HOOFDPROGRAMMA ───────────────────────────────────────────────────────────
print("Laden...")
df = pd.read_csv(INPUT, dtype=str)
missing = df[df['email'].isna()].copy()
print(f"Te verwerken: {len(missing)} bedrijven zonder email")
print(f"Baseline: {df['email'].notna().sum()}/500\n")

step1_found = 0
step2_found = 0
step3_found = 0
step4_found = 0

for i, (idx, row) in enumerate(missing.iterrows()):
    naam     = str(row['naam'])
    gemeente = str(row['gemeente']) if pd.notna(row['gemeente']) else ''

    if i % 25 == 0:
        total_now = df['email'].notna().sum()
        print(f"  [{i}/{len(missing)}] Emails gevonden tot nu: {total_now} | "
              f"DDG:{step1_found} Scrape:{step2_found} Gids:{step3_found} Gok:{step4_found}",
              flush=True)

    # Gebruik bestaande website als die bekend is
    website = row.get('website') if pd.notna(row.get('website', None)) else None

    # Stap 1: DuckDuckGo zoeken naar website
    if not website:
        website = ddg_find_website(naam, gemeente)
        if website:
            df.loc[idx, 'website'] = website
            step1_found += 1
        time.sleep(2)

    # Stap 2: Scrape website
    if website:
        email = get_email_from_website(str(website))
        if email:
            df.loc[idx, 'email'] = email
            df.loc[idx, 'email_bron'] = 'duckduckgo-scrape'
            step2_found += 1
            continue
        time.sleep(0.5)

    # Stap 3: Gouden Gids fallback
    email = goudengids_search(naam, gemeente)
    if email:
        df.loc[idx, 'email'] = email
        df.loc[idx, 'email_bron'] = 'goudengids'
        step3_found += 1
        time.sleep(2)
        continue
    time.sleep(1)

    # Stap 4: info@domein constructie
    if website:
        domain = urlparse(str(website)).netloc.replace('www.', '')
        if domain:
            df.loc[idx, 'email'] = f'info@{domain}'
            df.loc[idx, 'email_bron'] = 'domein-gok'
            step4_found += 1

# ─── EINDRAPPORT ──────────────────────────────────────────────────────────────
final_total = df['email'].notna().sum()
print("\n" + "="*60)
print("EINDRAPPORT")
print("="*60)
print(f"Baseline:              185/500 (37%)")
print(f"Nieuwe emails gevonden via DDG-zoeken: {step1_found} websites")
print(f"  → scrape:      {step2_found}")
print(f"  → goudengids:  {step3_found}")
print(f"  → domein-gok:  {step4_found}")
print(f"\nTotaal nu: {final_total}/500 ({final_total/5:.1f}%)")
print(f"\nVerdeling per bron:")
print(df['email_bron'].value_counts().to_string())
print(f"\nNog steeds leeg: {df['email'].isna().sum()}")

df.to_csv(OUTPUT, index=False)
print(f"\nOpgeslagen: {OUTPUT}")
