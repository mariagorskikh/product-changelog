"""Shared helpers for the product-changelog scripts.

Stdlib only, plus PyYAML for reading config.yaml.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PLACEHOLDERS = ("PRODUCT_NAME", "SENDER_NAME", "FROM_EMAIL", "AUDIENCE_ID", "YOUR_NAME", "yourproduct.example")

# Some API edges (Cloudflare in front of Resend among them) reject urllib's
# default User-Agent with a 403, so send an ordinary browser one.
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) product-changelog"


def die(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------- config

def load_config(path: str | None = None) -> dict:
    candidates = [path, os.environ.get("CHANGELOG_CONFIG"), "config.yaml", str(SKILL_DIR / "config.yaml")]
    for c in candidates:
        if c and Path(c).is_file():
            try:
                import yaml  # type: ignore
            except ImportError:
                die("PyYAML is required: pip install pyyaml")
            with open(c) as f:
                cfg = yaml.safe_load(f) or {}
            cfg["_path"] = str(Path(c).resolve())
            return cfg
    die("no config.yaml found. Copy config.example.yaml to config.yaml and fill it in, "
        "or pass --config PATH / set CHANGELOG_CONFIG.")
    return {}


def get(cfg: dict, dotted: str, default=None):
    cur = cfg
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def require(cfg: dict, dotted: str) -> str:
    val = get(cfg, dotted)
    if val in (None, ""):
        die(f"config value '{dotted}' is missing in {cfg.get('_path')}")
    if isinstance(val, str) and any(p in val for p in PLACEHOLDERS):
        die(f"config value '{dotted}' is still a placeholder ({val!r}) in {cfg.get('_path')}")
    return val


def from_header(cfg: dict) -> str:
    return f"{require(cfg, 'sender.from_display')} <{require(cfg, 'sender.from_email')}>"


def api_key(cfg: dict) -> str:
    env = get(cfg, "provider.api_key_env", "RESEND_API_KEY")
    key = os.environ.get(env, "").strip()
    if not key:
        die(f"environment variable {env} is not set")
    return key


# ---------------------------------------------------------------- people

def first_name(raw: str | None) -> str:
    """First usable token of a display name, or '' to use the fallback.

    Rejects tokens with '@' or digits, without letters, or outside 2..20
    characters. Capitalizes all-lowercase names and shouting all-caps ones.
    """
    if not raw:
        return ""
    toks = raw.strip().split()
    if not toks:
        return ""
    fn = toks[0].strip(".,;:()[]\"'")
    if not fn or "@" in fn or any(ch.isdigit() for ch in fn):
        return ""
    if not any(ch.isalpha() for ch in fn):
        return ""
    if len(fn) < 2 or len(fn) > 20:
        return ""
    if fn.islower():
        fn = fn[0].upper() + fn[1:]
    elif fn.isupper() and len(fn) > 3:
        fn = fn.capitalize()
    return fn


def read_email_set(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {line.strip().lower() for line in path.open() if line.strip() and not line.startswith("#")}


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.open():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


# ---------------------------------------------------------------- unsubscribe

def unsubscribe_url(cfg: dict, email: str) -> str:
    """Signed, personal unsubscribe link for the own_endpoint mode.

    token = base64url(HMAC-SHA256(secret, lowercase email)), no padding.
    Your endpoint recomputes it to verify, so links never expire and
    cannot be forged for another address.
    """
    template = require(cfg, "unsubscribe.url_template")
    secret_env = get(cfg, "unsubscribe.secret_env", "UNSUBSCRIBE_SECRET")
    secret = os.environ.get(secret_env, "")
    if not secret:
        die(f"environment variable {secret_env} is not set (needed to sign unsubscribe links)")
    e = email.strip().lower()
    digest = hmac.new(secret.encode(), e.encode(), hashlib.sha256).digest()
    token = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    return template.format(email=urllib.parse.quote(e), token=token)


def personalize(template: str, name: str, unsub: str) -> str:
    return template.replace("{{NAME}}", name).replace("{{UNSUB_URL}}", unsub)


def read_issue(workdir: Path) -> tuple[str, str, str]:
    for f in ("email.html", "email.txt", "subject.txt"):
        if not (workdir / f).exists():
            die(f"{workdir / f} is missing")
    subject = (workdir / "subject.txt").read_text().strip()
    if not subject:
        die("subject.txt is empty")
    return (workdir / "email.html").read_text(), (workdir / "email.txt").read_text(), subject


# ---------------------------------------------------------------- HTTP

class Resend:
    BASE = "https://api.resend.com"

    def __init__(self, key: str):
        self.key = key

    def request(self, method: str, path: str, body: dict | None = None, retries: int = 4) -> tuple[int, dict | str]:
        url = path if path.startswith("http") else self.BASE + path
        data = json.dumps(body).encode() if body is not None else None
        last = ""
        for attempt in range(retries):
            req = urllib.request.Request(url, data=data, method=method, headers={
                "Authorization": f"Bearer {self.key}",
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            })
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    raw = r.read().decode() or "{}"
                    return r.status, _maybe_json(raw)
            except urllib.error.HTTPError as ex:
                raw = ex.read().decode(errors="replace")
                if ex.code == 429 or ex.code >= 500:
                    wait = 2.0 + attempt
                    try:
                        wait = max(wait, float(ex.headers.get("retry-after") or 0))
                    except ValueError:
                        pass
                    last = f"{ex.code}: {raw[:200]}"
                    time.sleep(wait)
                    continue
                return ex.code, _maybe_json(raw)
            except (urllib.error.URLError, TimeoutError) as ex:
                last = f"connection error: {ex}"
                time.sleep(2 + attempt)
        return 0, f"retries exhausted ({last})"

    def list_contacts(self, audience_id: str) -> list[dict]:
        """Every contact in an audience, following cursor pages when offered."""
        out: list[dict] = []
        after = None
        while True:
            q = "?limit=100" + (f"&after={after}" if after else "")
            status, body = self.request("GET", f"/audiences/{audience_id}/contacts{q}")
            if status != 200 or not isinstance(body, dict):
                die(f"listing contacts failed: {status} {str(body)[:200]}")
            page = body.get("data") or []
            out.extend(page)
            if not body.get("has_more") or not page:
                break
            after = page[-1].get("id")
        return out


def _maybe_json(raw: str):
    try:
        return json.loads(raw)
    except ValueError:
        return raw
