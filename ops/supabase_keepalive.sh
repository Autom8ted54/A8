#!/bin/zsh
# Keeps the free Supabase project from pausing (pauses after 7 days idle).
# Temporary: remove once the weekly digest runs in GitHub Actions.
# Logs only the HTTP status, never the key.
set -eu
ENV_FILE="/Users/NomadFilip/kansenradar/.env"
URL=$(grep '^SUPABASE_URL=' "$ENV_FILE" | cut -d= -f2-)
KEY=$(grep '^SUPABASE_SERVICE_KEY=' "$ENV_FILE" | cut -d= -f2-)
CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 30 \
  -H "apikey: $KEY" "$URL/rest/v1/waitlist_signups?select=id&limit=1" || echo "000")
echo "$(date '+%Y-%m-%d %H:%M') supabase keepalive HTTP $CODE"
