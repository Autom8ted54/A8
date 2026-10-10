<?php
/**
 * Kansenradar — wachtlijst-endpoint (mijn.host, PHP)
 * POST api/waitlist.php  (JSON body)
 *
 * 1. Valideert de inschrijving (zelfde regels als vroeger in functions/api/waitlist.js)
 * 2. Insert in Supabase waitlist_signups via REST
 * 3. Stuurt een bedankmail met voorbeeld-digest via Resend (sample-digest.html)
 *
 * Secrets komen uit config.php (niet in git, aangemaakt door deploy.sh vanuit .env).
 * KR_CONFIG env var overschrijft het pad (gebruikt door tests).
 */

declare(strict_types=1);

// Waarschuwingen nooit in de JSON-respons; ze gaan naar de serverlog
ini_set('display_errors', '0');

const ALLOWED_SCHRIJFT_AL_IN = ['ja', 'soms', 'nee'];
const ALLOWED_UREN_PER_WEEK = ['0', '1-2', '3-5', '5+'];
const ALLOWED_GEBRUIKT_TOOL = ['ja-tenderwolf', 'ja-andere', 'nee'];
const ALLOWED_MEDEWERKERS = ['1-5', '6-15', '16-30', '30+'];
const ALLOWED_INTERESSE = ['uitproberen', 'meer-zien', 'nieuwsgierig'];

function json_response(array $data, int $status = 200): void
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($data, JSON_UNESCAPED_UNICODE);
    exit;
}

function load_config(): array
{
    $path = getenv('KR_CONFIG') ?: __DIR__ . '/config.php';
    if (!is_file($path)) {
        return [];
    }
    $config = require $path;
    return is_array($config) ? $config : [];
}

/** Supabase-headers. Nieuwe sb_secret_-sleutels gaan enkel in `apikey`; legacy JWT-sleutels (eyJ...) ook als Bearer. */
function supabase_headers(string $key): array
{
    $headers = ['Content-Type: application/json', 'apikey: ' . $key, 'Prefer: return=minimal'];
    if (str_starts_with($key, 'eyJ')) {
        $headers[] = 'Authorization: Bearer ' . $key;
    }
    return $headers;
}

/** @return array{0:int,1:string} [status, body]; status 0 bij verbindingsfout */
function http_request(string $method, string $url, array $headers, string $body): array
{
    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_CUSTOMREQUEST => $method,
        CURLOPT_HTTPHEADER => $headers,
        CURLOPT_POSTFIELDS => $body,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT => 10,
    ]);
    $response = curl_exec($ch);
    $status = $response === false ? 0 : (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
    return [$status, $response === false ? '' : (string) $response];
}

function send_sample_mail(array $config, string $email): bool
{
    $resendKey = $config['RESEND_API_KEY'] ?? '';
    $samplePath = __DIR__ . '/sample-digest.html';
    if ($resendKey === '' || !is_file($samplePath)) {
        error_log('Kansenradar: bedankmail overgeslagen (geen RESEND_API_KEY of sample-digest.html).');
        return false;
    }
    $from = $config['FROM_EMAIL'] ?? 'hallo@kansenradar.be';
    $payload = [
        'from' => 'Kansenradar <' . $from . '>',
        'to' => [$email],
        'reply_to' => $config['REPLY_TO'] ?? 'hallo@kansenradar.be',
        'subject' => 'Je staat op de lijst — hier is een voorbeeld van je Kansenradar',
        'html' => file_get_contents($samplePath),
    ];
    $resendUrl = rtrim($config['RESEND_URL'] ?? 'https://api.resend.com', '/') . '/emails';
    [$status, $body] = http_request('POST', $resendUrl, [
        'Content-Type: application/json',
        'Authorization: Bearer ' . $resendKey,
    ], json_encode($payload, JSON_UNESCAPED_UNICODE));
    if ($status < 200 || $status >= 300) {
        error_log('Kansenradar: Resend fout ' . $status . ': ' . $body);
        return false;
    }
    return true;
}

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    json_response(['error' => 'Methode niet toegestaan.'], 405);
}

$body = json_decode((string) file_get_contents('php://input'), true);
if (!is_array($body)) {
    json_response(['error' => 'Ongeldig verzoek.'], 400);
}

$email = $body['email'] ?? null;
$frustratie = $body['grootste_frustratie'] ?? '';
$website = $body['website'] ?? '';
$bron = $body['bron'] ?? '';

// Honeypot: bots vullen het verborgen veld in — doe alsof het lukte
if ($website !== '' && $website !== null) {
    json_response(['success' => true]);
}

$errors = [];
if (!is_string($email) || !preg_match('/^[^\s@]+@[^\s@]+\.[^\s@]+$/', trim($email))) {
    $errors[] = 'Ongeldig e-mailadres.';
}
if (!is_string($frustratie)) {
    $errors[] = 'Ongeldige waarde voor grootste_frustratie.';
}
if (!is_string($bron)) {
    $errors[] = 'Ongeldige waarde voor bron.';
}
$enums = [
    'schrijft_al_in' => ALLOWED_SCHRIJFT_AL_IN,
    'uren_per_week' => ALLOWED_UREN_PER_WEEK,
    'gebruikt_tool' => ALLOWED_GEBRUIKT_TOOL,
    'aantal_medewerkers' => ALLOWED_MEDEWERKERS,
    'interesse' => ALLOWED_INTERESSE,
];
foreach ($enums as $field => $allowed) {
    if (!in_array($body[$field] ?? null, $allowed, true)) {
        $errors[] = 'Ongeldige waarde voor ' . $field . '.';
    }
}
if ($errors) {
    json_response(['error' => $errors[0]], 400);
}

$config = load_config();
$supabaseUrl = $config['SUPABASE_URL'] ?? '';
$supabaseKey = $config['SUPABASE_SERVICE_KEY'] ?? '';
if ($supabaseUrl === '' || $supabaseKey === '') {
    error_log('Kansenradar: SUPABASE_URL of SUPABASE_SERVICE_KEY niet ingesteld.');
    json_response(['error' => 'Serverconfiguratiefout. Probeer later opnieuw.'], 500);
}

$email = strtolower(trim($email));
$bron = substr((string) preg_replace('/[^a-z0-9_-]/', '', strtolower($bron)), 0, 40);
$payload = [
    'email' => $email,
    'schrijft_al_in' => $body['schrijft_al_in'],
    'uren_per_week' => $body['uren_per_week'],
    'gebruikt_tool' => $body['gebruikt_tool'],
    'grootste_frustratie' => mb_substr(trim($frustratie), 0, 1000),
    'aantal_medewerkers' => $body['aantal_medewerkers'],
    'interesse' => $body['interesse'],
    'source' => $bron !== '' ? $bron : 'landing_page',
];

$table = rtrim($supabaseUrl, '/') . '/rest/v1/waitlist_signups';
[$status, $resBody] = http_request('POST', $table, supabase_headers($supabaseKey), json_encode($payload, JSON_UNESCAPED_UNICODE));

if ($status === 0) {
    json_response(['error' => 'Kan geen verbinding maken. Probeer het opnieuw.'], 503);
}
// Duplicate email — Supabase geeft 409 bij UNIQUE-schending
if ($status === 409) {
    json_response(['error' => 'Dit e-mailadres staat al op de wachtlijst.'], 409);
}
if ($status !== 201) {
    error_log('Kansenradar: Supabase fout ' . $status . ': ' . $resBody);
    json_response(['error' => 'Er is iets misgegaan. Probeer later opnieuw.'], 500);
}

// Inschrijving is binnen; een mislukte bedankmail mag de inschrijving niet doen falen
if (send_sample_mail($config, $email)) {
    http_request('PATCH', $table . '?email=eq.' . rawurlencode($email), supabase_headers($supabaseKey),
        json_encode(['sample_sent_at' => gmdate('c')]));
}

json_response(['success' => true]);
