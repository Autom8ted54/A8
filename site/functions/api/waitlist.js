/**
 * Kansenradar — Cloudflare Pages Function
 * POST /api/waitlist
 *
 * Validates form submission and inserts into Supabase waitlist_signups table.
 * Environment variables (set in Cloudflare Pages dashboard):
 *   SUPABASE_URL            — https://<project-id>.supabase.co
 *   SUPABASE_SERVICE_KEY    — service role key (bypasses RLS)
 */

const ALLOWED_SCHRIJFT_AL_IN = ['ja', 'soms', 'nee'];
const ALLOWED_UREN_PER_WEEK = ['0', '1-2', '3-5', '5+'];
const ALLOWED_GEBRUIKT_TOOL = ['ja-tenderwolf', 'ja-andere', 'nee'];
const ALLOWED_MEDEWERKERS = ['1-5', '6-15', '16-30', '30+'];

function isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function jsonResponse(data, status = 200) {
    return new Response(JSON.stringify(data), {
        status,
        headers: {
            'Content-Type': 'application/json',
            // Restrict to same origin — form and function are on kansenradar.be
            'Access-Control-Allow-Origin': 'https://kansenradar.be',
        },
    });
}

export async function onRequestPost(context) {
    const { request, env } = context;

    // Parse body
    let body;
    try {
        body = await request.json();
    } catch {
        return jsonResponse({ error: 'Ongeldig verzoek.' }, 400);
    }

    const {
        email,
        schrijft_al_in,
        uren_per_week,
        gebruikt_tool,
        grootste_frustratie = '',
        aantal_medewerkers,
    } = body;

    // Server-side validatie
    const errors = [];

    if (!email || !isValidEmail(email.trim())) {
        errors.push('Ongeldig e-mailadres.');
    }
    if (!ALLOWED_SCHRIJFT_AL_IN.includes(schrijft_al_in)) {
        errors.push('Ongeldige waarde voor schrijft_al_in.');
    }
    if (!ALLOWED_UREN_PER_WEEK.includes(uren_per_week)) {
        errors.push('Ongeldige waarde voor uren_per_week.');
    }
    if (!ALLOWED_GEBRUIKT_TOOL.includes(gebruikt_tool)) {
        errors.push('Ongeldige waarde voor gebruikt_tool.');
    }
    if (!ALLOWED_MEDEWERKERS.includes(aantal_medewerkers)) {
        errors.push('Ongeldige waarde voor aantal_medewerkers.');
    }

    if (errors.length > 0) {
        return jsonResponse({ error: errors[0] }, 400);
    }

    // Supabase insert via REST API
    const supabaseUrl = env.SUPABASE_URL;
    const supabaseKey = env.SUPABASE_SERVICE_KEY;

    if (!supabaseUrl || !supabaseKey) {
        console.error('Kansenradar: SUPABASE_URL of SUPABASE_SERVICE_KEY niet ingesteld.');
        return jsonResponse({ error: 'Serverconfiguratiefout. Probeer later opnieuw.' }, 500);
    }

    const payload = {
        email: email.trim().toLowerCase(),
        schrijft_al_in,
        uren_per_week,
        gebruikt_tool,
        grootste_frustratie: grootste_frustratie.trim().slice(0, 1000), // max 1000 chars
        aantal_medewerkers,
        source: 'landing_page',
    };

    let supabaseRes;
    try {
        supabaseRes = await fetch(`${supabaseUrl}/rest/v1/waitlist_signups`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'apikey': supabaseKey,
                'Authorization': `Bearer ${supabaseKey}`,
                'Prefer': 'return=minimal',
            },
            body: JSON.stringify(payload),
        });
    } catch (err) {
        console.error('Kansenradar: Supabase fetch fout:', err);
        return jsonResponse({ error: 'Kan geen verbinding maken. Probeer het opnieuw.' }, 503);
    }

    if (supabaseRes.status === 201) {
        return jsonResponse({ success: true });
    }

    // Duplicate email — Supabase returns 409 for UNIQUE constraint violations
    if (supabaseRes.status === 409) {
        return jsonResponse({ error: 'Dit e-mailadres staat al op de wachtlijst.' }, 409);
    }

    // Unexpected Supabase error
    const errBody = await supabaseRes.text();
    console.error('Kansenradar: Supabase fout:', supabaseRes.status, errBody);
    return jsonResponse({ error: 'Er is iets misgegaan. Probeer later opnieuw.' }, 500);
}

// Handle OPTIONS preflight (same-origin so not strictly needed, but safe to include)
export async function onRequestOptions() {
    return new Response(null, {
        status: 204,
        headers: {
            'Access-Control-Allow-Origin': 'https://kansenradar.be',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
        },
    });
}
