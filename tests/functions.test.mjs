// Tests voor de Cloudflare Pages Functions (waitlist + unsubscribe).
// Draaien zonder Cloudflare of Supabase: fetch wordt gemockt.
// Run: node --test tests/functions.test.mjs

import test from 'node:test';
import assert from 'node:assert/strict';

import { onRequestPost as waitlistPost } from '../site/functions/api/waitlist.js';
import { onRequestGet as unsubscribeGet } from '../site/functions/unsubscribe.js';

const ENV = { SUPABASE_URL: 'https://fake.supabase.co', SUPABASE_SERVICE_KEY: 'service-key' };

const VALID_BODY = {
    email: 'test@bureau.be',
    schrijft_al_in: 'ja',
    uren_per_week: '1-2',
    gebruikt_tool: 'nee',
    grootste_frustratie: 'te veel ruis',
    aantal_medewerkers: '1-5',
};

function waitlistRequest(body) {
    return new Request('https://kansenradar.be/api/waitlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
}

function mockFetch(status, jsonBody = null) {
    const calls = [];
    globalThis.fetch = async (url, opts) => {
        calls.push({ url, opts });
        return new Response(jsonBody === null ? '' : JSON.stringify(jsonBody), { status });
    };
    return calls;
}

test('waitlist: geldige inzending → 200 + Supabase insert', async () => {
    const calls = mockFetch(201);
    const res = await waitlistPost({ request: waitlistRequest(VALID_BODY), env: ENV });
    assert.equal(res.status, 200);
    assert.deepEqual(await res.json(), { success: true });
    assert.equal(calls.length, 1);
    assert.match(calls[0].url, /\/rest\/v1\/waitlist_signups$/);
    const payload = JSON.parse(calls[0].opts.body);
    assert.equal(payload.email, 'test@bureau.be');
});

test('waitlist: e-mail wordt genormaliseerd (trim + lowercase)', async () => {
    const calls = mockFetch(201);
    await waitlistPost({ request: waitlistRequest({ ...VALID_BODY, email: '  Test@Bureau.BE ' }), env: ENV });
    assert.equal(JSON.parse(calls[0].opts.body).email, 'test@bureau.be');
});

test('waitlist: ongeldig e-mailadres → 400, geen Supabase-call', async () => {
    const calls = mockFetch(201);
    const res = await waitlistPost({ request: waitlistRequest({ ...VALID_BODY, email: 'geen-email' }), env: ENV });
    assert.equal(res.status, 400);
    assert.equal(calls.length, 0);
});

test('waitlist: ongeldige radio-waarde → 400', async () => {
    mockFetch(201);
    const res = await waitlistPost({ request: waitlistRequest({ ...VALID_BODY, uren_per_week: '100' }), env: ENV });
    assert.equal(res.status, 400);
});

test('waitlist: honeypot ingevuld → nep-succes zonder insert', async () => {
    const calls = mockFetch(201);
    const res = await waitlistPost({ request: waitlistRequest({ ...VALID_BODY, website: 'spam.com' }), env: ENV });
    assert.equal(res.status, 200);
    assert.deepEqual(await res.json(), { success: true });
    assert.equal(calls.length, 0);
});

test('waitlist: non-string frustratie → 400 in plaats van crash', async () => {
    mockFetch(201);
    const res = await waitlistPost({ request: waitlistRequest({ ...VALID_BODY, grootste_frustratie: 123 }), env: ENV });
    assert.equal(res.status, 400);
});

test('waitlist: kapotte JSON body → 400', async () => {
    mockFetch(201);
    const req = new Request('https://kansenradar.be/api/waitlist', { method: 'POST', body: '{niet json' });
    const res = await waitlistPost({ request: req, env: ENV });
    assert.equal(res.status, 400);
});

test('waitlist: dubbel e-mailadres (Supabase 409) → 409 met NL-melding', async () => {
    mockFetch(409);
    const res = await waitlistPost({ request: waitlistRequest(VALID_BODY), env: ENV });
    assert.equal(res.status, 409);
    const body = await res.json();
    assert.match(body.error, /al op de wachtlijst/);
});

test('waitlist: ontbrekende env vars → 500 zonder crash', async () => {
    mockFetch(201);
    const res = await waitlistPost({ request: waitlistRequest(VALID_BODY), env: {} });
    assert.equal(res.status, 500);
});

const TOKEN = '123e4567-e89b-42d3-a456-426614174000';

function unsubscribeRequest(token) {
    return new Request(`https://kansenradar.be/unsubscribe?token=${token}`);
}

test('unsubscribe: geldig token + match → 200 bevestiging', async () => {
    const calls = mockFetch(200, [{ id: '1', active: false }]);
    const res = await unsubscribeGet({ request: unsubscribeRequest(TOKEN), env: ENV });
    assert.equal(res.status, 200);
    assert.match(await res.text(), /uitgeschreven/);
    assert.equal(calls[0].opts.method, 'PATCH');
    assert.match(calls[0].url, new RegExp(`unsubscribe_token=eq\\.${TOKEN}`));
    assert.deepEqual(JSON.parse(calls[0].opts.body), { active: false });
});

test('unsubscribe: onbekend token (lege match) → 404', async () => {
    mockFetch(200, []);
    const res = await unsubscribeGet({ request: unsubscribeRequest(TOKEN), env: ENV });
    assert.equal(res.status, 404);
});

test('unsubscribe: geen geldig UUID → 400, geen Supabase-call', async () => {
    const calls = mockFetch(200, []);
    const res = await unsubscribeGet({ request: unsubscribeRequest('DROP TABLE'), env: ENV });
    assert.equal(res.status, 400);
    assert.equal(calls.length, 0);
});

test('unsubscribe: ontbrekend token → 400', async () => {
    mockFetch(200, []);
    const res = await unsubscribeGet({ request: new Request('https://kansenradar.be/unsubscribe'), env: ENV });
    assert.equal(res.status, 400);
});
