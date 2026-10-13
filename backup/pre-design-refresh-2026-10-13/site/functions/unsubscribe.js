/**
 * Kansenradar — Cloudflare Pages Function
 * GET  /unsubscribe?token=<uuid>  — bevestigingspagina + uitschrijving
 * POST /unsubscribe?token=<uuid>  — one-click unsubscribe (RFC 8058, Gmail/Yahoo)
 *
 * Zet subscribers.active = false op basis van unsubscribe_token.
 * Environment variables (Cloudflare Pages dashboard):
 *   SUPABASE_URL, SUPABASE_SERVICE_KEY
 */

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function htmlPage(title, message, status = 200) {
    const body = `<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex">
<title>${title} — Kansenradar</title>
<style>
  body{margin:0;font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#F0F2F5;color:#1B2B4B;display:flex;min-height:100vh;align-items:center;justify-content:center;padding:24px;box-sizing:border-box}
  .card{background:#fff;border-radius:12px;box-shadow:0 4px 6px rgba(0,0,0,.05),0 10px 40px rgba(0,0,0,.1);padding:40px 32px;max-width:440px;text-align:center}
  h1{font-size:1.35rem;margin:0 0 12px}
  p{color:#64748B;font-size:.95rem;line-height:1.6;margin:0}
  a{color:#D4911A;font-weight:600;text-decoration:none}
</style>
</head>
<body><div class="card"><h1>${title}</h1><p>${message}</p></div></body>
</html>`;
    return new Response(body, {
        status,
        headers: { 'Content-Type': 'text/html; charset=utf-8' },
    });
}

async function unsubscribe(context) {
    const { request, env } = context;
    const token = new URL(request.url).searchParams.get('token') || '';

    if (!UUID_RE.test(token)) {
        return htmlPage('Ongeldige link', 'Deze uitschrijflink is niet geldig. Mail naar <a href="mailto:filip@kansenradar.be">filip@kansenradar.be</a> als je je wil uitschrijven.', 400);
    }

    if (!env.SUPABASE_URL || !env.SUPABASE_SERVICE_KEY) {
        console.error('Kansenradar: SUPABASE_URL of SUPABASE_SERVICE_KEY niet ingesteld.');
        return htmlPage('Er ging iets mis', 'Probeer het later opnieuw of mail naar <a href="mailto:filip@kansenradar.be">filip@kansenradar.be</a>.', 500);
    }

    let res;
    try {
        res = await fetch(
            `${env.SUPABASE_URL}/rest/v1/subscribers?unsubscribe_token=eq.${token}`,
            {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'apikey': env.SUPABASE_SERVICE_KEY,
                    'Authorization': `Bearer ${env.SUPABASE_SERVICE_KEY}`,
                    'Prefer': 'return=representation',
                },
                body: JSON.stringify({ active: false }),
            }
        );
    } catch (err) {
        console.error('Kansenradar: Supabase fetch fout:', err);
        return htmlPage('Er ging iets mis', 'Kan geen verbinding maken. Probeer het later opnieuw.', 503);
    }

    if (!res.ok) {
        console.error('Kansenradar: Supabase fout:', res.status, await res.text());
        return htmlPage('Er ging iets mis', 'Probeer het later opnieuw of mail naar <a href="mailto:filip@kansenradar.be">filip@kansenradar.be</a>.', 500);
    }

    const rows = await res.json();
    if (!rows.length) {
        return htmlPage('Link niet gevonden', 'Deze uitschrijflink hoort bij geen enkel actief abonnement. Mogelijk ben je al uitgeschreven.', 404);
    }

    return htmlPage('Je bent uitgeschreven', 'Je ontvangt geen digests meer van Kansenradar. Van gedachten veranderd? Mail naar <a href="mailto:filip@kansenradar.be">filip@kansenradar.be</a>.');
}

export async function onRequestGet(context) {
    return unsubscribe(context);
}

// One-click unsubscribe: mailclients POSTen zonder de pagina te tonen
export async function onRequestPost(context) {
    return unsubscribe(context);
}
