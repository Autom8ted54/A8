import pandas as pd
import socket
import re
import smtplib
import unicodedata
import time
import requests
from requests.exceptions import RequestException

KBO_DIR   = '/Users/NomadFilip/kansenradar_kbo'
OUT_DIR   = '/Users/NomadFilip/Documents/kansenradar/output'
INPUT     = f'{OUT_DIR}/kansenradar_top_prospects_verrijkt.csv'
OUTPUT    = f'{OUT_DIR}/kansenradar_top_prospects_verrijkt.csv'

EMAIL_RE  = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
BLACKLIST = {'noreply','no-reply','mailer-daemon','postmaster','bounce','donotreply'}

def clean_email(email):
    e = email.strip().lower()
    local = e.split('@')[0]
    if local in BLACKLIST:
        return None
    return e

# ─── STAP 1: KBO vestigings-emails (EST) ──────────────────────────────────────
print("Stap 1 — KBO vestigings-emails (EST)...")

df = pd.read_csv(INPUT, dtype=str)
df['email_bron'] = df['email'].apply(lambda x: 'KBO-ENT' if pd.notna(x) else None)
baseline = df['email'].notna().sum()
print(f"  Baseline: {baseline} e-mails")

# Laad EST-emails uit contact.csv
contact = pd.read_csv(f'{KBO_DIR}/contact.csv', dtype=str)
est_emails = contact[
    (contact['ContactType'] == 'EMAIL') &
    (contact['EntityContact'] == 'EST')
][['EntityNumber', 'Value']].copy()
est_emails.columns = ['EstablishmentNumber', 'est_email']
est_emails['est_email'] = est_emails['est_email'].str.strip().str.lower()

# Laad establishment.csv: koppel EstablishmentNumber → EnterpriseNumber
estab = pd.read_csv(f'{KBO_DIR}/establishment.csv', dtype=str)
estab.columns = [c.strip().strip('"') for c in estab.columns]

# Koppel EST-email → EnterpriseNumber
est_merged = est_emails.merge(estab, on='EstablishmentNumber', how='left')
# Neem per onderneming eerste EST-email
est_per_ent = (est_merged.dropna(subset=['EnterpriseNumber'])
               .groupby('EnterpriseNumber')['est_email']
               .first()
               .reset_index())
est_per_ent.rename(columns={'EnterpriseNumber': 'ondernemingsnummer'}, inplace=True)

# Vul aan waar ENT-email ontbreekt
df = df.merge(est_per_ent, on='ondernemingsnummer', how='left')
mask_est = df['email'].isna() & df['est_email'].notna()
df.loc[mask_est, 'email'] = df.loc[mask_est, 'est_email']
df.loc[mask_est, 'email_bron'] = 'KBO-EST'
df.drop(columns=['est_email'], inplace=True)

after_step1 = df['email'].notna().sum()
print(f"  Na stap 1: {after_step1} e-mails (+{after_step1 - baseline})")

# ─── HULPFUNCTIES STAP 2 ──────────────────────────────────────────────────────

def slugify(name):
    """Bedrijfsnaam → domeinkandidaat."""
    name = name.lower()
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
    name = re.sub(r'\b(bv|nv|vzw|cvba|cvoa|srl|sa|asbl|bvba|comm\.v|the|and|en|de|het|van|voor|&)\b', '', name)
    name = re.sub(r'[^a-z0-9]+', '', name)
    return name.strip()

def domain_exists(domain):
    try:
        socket.getaddrinfo(domain, None, socket.AF_INET)
        return True
    except socket.gaierror:
        return False

def scrape_emails(url, timeout=6):
    """Haal emails op van een URL."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; KansenradarBot/1.0)'}
        r = requests.get(url, timeout=timeout, headers=headers, allow_redirects=True)
        if r.status_code == 200:
            emails = EMAIL_RE.findall(r.text)
            cleaned = [clean_email(e) for e in emails]
            cleaned = [e for e in cleaned if e and not e.endswith(('.png','.jpg','.gif','.css','.js'))]
            # Voorkeur voor info@, contact@, hello@ boven persoonlijke adressen
            prio = [e for e in cleaned if e.split('@')[0] in ('info','contact','hello','hallo','post','mail','office')]
            return prio[0] if prio else (cleaned[0] if cleaned else None)
    except RequestException:
        pass
    return None

def find_website_and_email(naam, known_website=None):
    """Stap 2: leid domein af, zoek email op website."""
    slug = slugify(str(naam))
    if not slug:
        return None, None

    tlds = ['.be', '.com', '.eu', '.agency', '.studio', '.brussels']
    found_domain = None

    if known_website and isinstance(known_website, str) and known_website.strip():
        # Normaliseer bekende website
        site = known_website.strip().lower()
        if not site.startswith('http'):
            site = 'http://' + site
        found_domain = site
    else:
        for tld in tlds:
            candidate = slug + tld
            if domain_exists(candidate):
                found_domain = 'https://' + candidate
                break

    if not found_domain:
        return None, None

    # Scrape homepage
    email = scrape_emails(found_domain)
    if not email:
        # Probeer /contact of /contact-us
        for path in ['/contact', '/contact-us', '/over-ons', '/contacteer-ons']:
            email = scrape_emails(found_domain + path)
            if email:
                break

    return found_domain, email

# ─── STAP 2: Website scrapen ──────────────────────────────────────────────────
print("\nStap 2 — Domeinen afleiden + websites scrapen...")

no_email = df[df['email'].isna()].copy()
print(f"  Te verwerken: {len(no_email)} prospects")

results = []
for i, (idx, row) in enumerate(no_email.iterrows()):
    if i % 50 == 0:
        print(f"  {i}/{len(no_email)}...", flush=True)
    website, email = find_website_and_email(row['naam'], row.get('website'))
    results.append((idx, website, email))
    time.sleep(0.2)  # Beleefd scrapen

for idx, website, email in results:
    if website and pd.isna(df.loc[idx, 'website']):
        df.loc[idx, 'website'] = website
    if email:
        df.loc[idx, 'email'] = email
        df.loc[idx, 'email_bron'] = 'website-scrape'

after_step2 = df['email'].notna().sum()
print(f"  Na stap 2: {after_step2} e-mails (+{after_step2 - after_step1})")

# ─── STAP 3: info@domein + SMTP-verificatie ───────────────────────────────────
print("\nStap 3 — info@domein constructie + SMTP-verificatie...")

def smtp_verify(email, timeout=5):
    """Controleer of een e-mailadres bestaat via SMTP handshake."""
    domain = email.split('@')[1]
    try:
        mx_records = socket.getaddrinfo(domain, 25)
        if not mx_records:
            return False
        mx_host = mx_records[0][4][0]
        with smtplib.SMTP(timeout=timeout) as smtp:
            smtp.connect(mx_host)
            smtp.helo('kansenradar.be')
            smtp.mail('check@kansenradar.be')
            code, _ = smtp.rcpt(email)
            return code == 250
    except Exception:
        return False

# Alleen voor prospects met een website maar nog geen email
still_missing = df[df['email'].isna() & df['website'].notna()].copy()
print(f"  Kandidaten (website bekend, geen email): {len(still_missing)}")

smtp_found = 0
for idx, row in still_missing.iterrows():
    site = str(row['website']).lower().replace('https://','').replace('http://','').rstrip('/')
    domain = site.split('/')[0]
    for prefix in ['info', 'hello', 'contact']:
        candidate = f'{prefix}@{domain}'
        if smtp_verify(candidate):
            df.loc[idx, 'email'] = candidate
            df.loc[idx, 'email_bron'] = 'domein-gok'
            smtp_found += 1
            break
    time.sleep(0.3)

after_step3 = df['email'].notna().sum()
print(f"  Na stap 3: {after_step3} e-mails (+{smtp_found} via SMTP)")

# ─── EINDRAPPORT ──────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("EINDRAPPORT E-MAIL VERRIJKING")
print("="*60)
print(f"Baseline (KBO-ENT):  {baseline}")
print(f"Na stap 1 (KBO-EST): {after_step1} (+{after_step1 - baseline})")
print(f"Na stap 2 (scrape):  {after_step2} (+{after_step2 - after_step1})")
print(f"Na stap 3 (SMTP):    {after_step3} (+{after_step3 - after_step2})")
print(f"\nTotale dekking: {after_step3}/500 ({after_step3/5:.1f}%)")
print(f"\nVerdeling per bron:")
print(df['email_bron'].value_counts().to_string())
print(f"\nNog steeds zonder email: {df['email'].isna().sum()}")

# Sla op
df.to_csv(OUTPUT, index=False)
print(f"\nOpgeslagen: {OUTPUT}")
