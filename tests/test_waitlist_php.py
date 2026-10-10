"""Tests for site/api/waitlist.php (mijn.host waitlist endpoint).

Runs the PHP built-in server against a local mock that stands in for Supabase and Resend.
Skipped when `php` is not installed.
"""

import json
import shutil
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

SITE_DIR = Path(__file__).resolve().parent.parent / "site"

pytestmark = pytest.mark.skipif(shutil.which("php") is None, reason="php not installed")

VALID_BODY = {
    "email": "test@bureau.be",
    "schrijft_al_in": "ja",
    "uren_per_week": "1-2",
    "gebruikt_tool": "nee",
    "grootste_frustratie": "te veel ruis",
    "aantal_medewerkers": "1-5",
    "interesse": "uitproberen",
    "bron": "mail1",
}


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class MockBackend:
    """Records requests; answers Supabase inserts with `insert_status`, everything else 200."""

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.insert_status = 201
        backend = self

        class Handler(BaseHTTPRequestHandler):
            def _handle(self) -> None:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode() if length else ""
                backend.calls.append(
                    {"method": self.command, "path": self.path, "headers": dict(self.headers), "body": body}
                )
                status = backend.insert_status if self.command == "POST" and "/rest/v1/" in self.path else 200
                self.send_response(status)
                self.end_headers()
                self.wfile.write(b"{}")

            do_POST = do_PATCH = _handle

            def log_message(self, *args) -> None:
                pass

        self.port = _free_port()
        self.server = HTTPServer(("127.0.0.1", self.port), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"


@pytest.fixture
def backend():
    b = MockBackend()
    yield b
    b.server.shutdown()


def _start_php(tmp_path: Path, config: dict | None) -> tuple[subprocess.Popen, str]:
    config_path = tmp_path / "config.php"
    if config is not None:
        entries = ",\n".join(f"    {json.dumps(k)} => {json.dumps(v)}" for k, v in config.items())
        config_path.write_text(f"<?php\nreturn [\n{entries}\n];\n")
    port = _free_port()
    proc = subprocess.Popen(
        ["php", "-S", f"127.0.0.1:{port}", "-t", str(SITE_DIR)],
        env={"KR_CONFIG": str(config_path), "PATH": "/usr/bin:/bin:/opt/homebrew/bin"},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.1).close()
            break
        except OSError:
            time.sleep(0.05)
    return proc, f"http://127.0.0.1:{port}/api/waitlist.php"


@pytest.fixture
def php(tmp_path, backend):
    started: list[subprocess.Popen] = []

    def start(config: dict | None = "default"):
        if config == "default":
            config = {
                "SUPABASE_URL": backend.url,
                "SUPABASE_SERVICE_KEY": "sb_secret_test",
                "RESEND_API_KEY": "re_test",
                "RESEND_URL": backend.url,
            }
        proc, url = _start_php(tmp_path, config)
        started.append(proc)
        return url

    yield start
    for p in started:
        p.terminate()
        p.wait()


def post(url: str, body) -> tuple[int, dict]:
    data = body if isinstance(body, bytes) else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as res:
            return res.status, json.loads(res.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def inserts(backend: MockBackend) -> list[dict]:
    return [c for c in backend.calls if c["method"] == "POST" and "/rest/v1/" in c["path"]]


def test_valid_signup_inserts_and_sends_sample(php, backend):
    status, body = post(php(), VALID_BODY)
    assert status == 200 and body == {"success": True}
    [insert] = inserts(backend)
    payload = json.loads(insert["body"])
    assert payload["email"] == "test@bureau.be"
    assert payload["interesse"] == "uitproberen"
    assert payload["source"] == "mail1"
    # sb_secret_ keys go only in the apikey header, never as Bearer JWT
    assert insert["headers"]["apikey"] == "sb_secret_test"
    assert "Authorization" not in insert["headers"]
    emails = [c for c in backend.calls if c["path"] == "/emails"]
    if (SITE_DIR / "api" / "sample-digest.html").is_file():
        assert len(emails) == 1
        assert json.loads(emails[0]["body"])["to"] == ["test@bureau.be"]
        assert any(c["method"] == "PATCH" for c in backend.calls)


def test_legacy_jwt_key_also_sent_as_bearer(php, backend):
    url = php({"SUPABASE_URL": backend.url, "SUPABASE_SERVICE_KEY": "eyJlegacy"})
    post(url, VALID_BODY)
    assert inserts(backend)[0]["headers"]["Authorization"] == "Bearer eyJlegacy"


def test_email_normalized_and_missing_bron_defaults(php, backend):
    body = {**VALID_BODY, "email": "  Test@Bureau.BE ", "bron": ""}
    post(php(), body)
    payload = json.loads(inserts(backend)[0]["body"])
    assert payload["email"] == "test@bureau.be"
    assert payload["source"] == "landing_page"


def test_bron_is_sanitized(php, backend):
    post(php(), {**VALID_BODY, "bron": "Mail<script>2"})
    assert json.loads(inserts(backend)[0]["body"])["source"] == "mailscript2"


def test_invalid_email_rejected_without_insert(php, backend):
    status, _ = post(php(), {**VALID_BODY, "email": "geen-email"})
    assert status == 400 and inserts(backend) == []


@pytest.mark.parametrize("field", ["uren_per_week", "interesse"])
def test_invalid_or_missing_choice_rejected(php, backend, field):
    status, _ = post(php(), {**VALID_BODY, field: "100"})
    assert status == 400
    missing = {k: v for k, v in VALID_BODY.items() if k != field}
    status, _ = post(php(), missing)
    assert status == 400


def test_honeypot_fakes_success_without_insert(php, backend):
    status, body = post(php(), {**VALID_BODY, "website": "spam.com"})
    assert status == 200 and body == {"success": True}
    assert backend.calls == []


def test_non_string_frustration_rejected(php, backend):
    status, _ = post(php(), {**VALID_BODY, "grootste_frustratie": 123})
    assert status == 400


def test_broken_json_rejected(php, backend):
    status, _ = post(php(), b"{niet json")
    assert status == 400


def test_duplicate_email_returns_409_without_mail(php, backend):
    backend.insert_status = 409
    status, body = post(php(), VALID_BODY)
    assert status == 409 and "al op de wachtlijst" in body["error"]
    assert not any(c["path"] == "/emails" for c in backend.calls)


def test_missing_config_returns_500(php, backend):
    status, _ = post(php(None), VALID_BODY)
    assert status == 500
