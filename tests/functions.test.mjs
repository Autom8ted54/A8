// Tests voor de Cloudflare Pages Function unsubscribe (digest-fase).
// De wachtlijst draait nu op mijn.host (site/api/waitlist.php) en wordt getest in tests/test_waitlist_php.py.
// Draaien zonder Cloudflare of Supabase: fetch wordt gemockt.
// Run: node --test tests/functions.test.mjs

import test from 'node:test';
import assert from 'node:assert/strict';

import { onRequestGet as unsubscribeGet } from '../site/functions/unsubscribe.js';

const ENV = { SUPABASE_URL: 'https://fake.supabase.co', SUPABASE_SERVICE_KEY: 'service-key' };

function mockFetch(status, jsonBody = null) {
    const calls = [];
    globalThis.fetch = async (url, opts) => {
        calls.push({ url, opts });
        return new Response(jsonBody === null ? '' : JSON.stringify(jsonBody), { status });
    };
    return calls;
}

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
