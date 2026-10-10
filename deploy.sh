#!/bin/bash
set -euo pipefail

# Deploy site/ naar kansenradar.be (mijn.host) via FTP.
# Leest uit .env: FTP_HOST, FTP_USER, FTP_PASS, SUPABASE_URL, SUPABASE_SERVICE_KEY, RESEND_API_KEY, FROM_EMAIL
# Genereert site/api/config.php (secrets, niet in git) voor waitlist.php.
# Gebruik: ./deploy.sh            → deploy
#          ./deploy.sh --check    → enkel verbinding testen + remote root tonen

cd "$(dirname "$0")"

if [[ ! -f .env ]]; then
  echo "❌ .env niet gevonden in $(pwd)"
  exit 1
fi
set -a; source .env; set +a

for v in FTP_HOST FTP_USER FTP_PASS; do
  if [[ -z "${!v:-}" ]]; then echo "❌ $v ontbreekt in .env"; exit 1; fi
done

nc -z -w6 "$FTP_HOST" 21 || { echo "❌ Poort 21 op $FTP_HOST onbereikbaar (ander netwerk/VPN?)"; exit 1; }

LFTP_OPEN="set ftp:ssl-allow no; set net:max-retries 3; set net:timeout 15; open -u $FTP_USER,$FTP_PASS ftp://$FTP_HOST"

# Scoped mijn.host-accounts landen soms in de domeinmap (met public_html/), soms rechtstreeks in de webroot
ROOT_LISTING=$(lftp -c "$LFTP_OPEN; cls -1 /")
if grep -qxE "/?public_html/?" <<<"$ROOT_LISTING"; then REMOTE_PATH=/public_html; else REMOTE_PATH=/; fi

if [[ "${1:-}" == "--check" ]]; then
  echo "✓ Verbonden met $FTP_HOST. Remote root:"
  echo "$ROOT_LISTING"
  echo "→ Deploy-doel: $REMOTE_PATH"
  exit 0
fi

for v in SUPABASE_URL SUPABASE_SERVICE_KEY RESEND_API_KEY; do
  if [[ -z "${!v:-}" ]]; then echo "❌ $v ontbreekt in .env"; exit 1; fi
done

# config.php met secrets (var_export-veilig via PHP-quoting)
php -r '
$c = [
  "SUPABASE_URL" => getenv("SUPABASE_URL"),
  "SUPABASE_SERVICE_KEY" => getenv("SUPABASE_SERVICE_KEY"),
  "RESEND_API_KEY" => getenv("RESEND_API_KEY"),
  "FROM_EMAIL" => getenv("FROM_EMAIL") ?: "hallo@kansenradar.be",
  "REPLY_TO" => "hallo@kansenradar.be",
];
file_put_contents("site/api/config.php", "<?php\nreturn " . var_export($c, true) . ";\n");
'
chmod 644 site/api/config.php

# lftp mirror behoudt bronrechten: 0600 geeft 403 op de server
find site -type f -exec chmod 644 {} +
find site -type d -exec chmod 755 {} +

echo "→ Sync site/ naar $FTP_HOST$REMOTE_PATH"
lftp -c "
$LFTP_OPEN;
mirror --reverse --parallel=4 --verbose \
  --exclude-glob functions/ --exclude-glob .DS_Store \
  site/ $REMOTE_PATH;
"

echo "✓ kansenradar.be deployed — check: https://kansenradar.be"
