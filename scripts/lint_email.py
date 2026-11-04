#!/usr/bin/env python3
"""Lint a changelog issue before any send. Read-only.

    python3 scripts/lint_email.py ISSUE_DIR                 # copy checks
    python3 scripts/lint_email.py ISSUE_DIR --check-links   # also fetch every link and image

Checks:
  - subject.txt exists, is not "Changelog #N", and is under 70 characters
  - em and en dashes (also as HTML entities) when voice.no_dashes is true
  - banned phrases from voice.banned_phrases
  - leftover draft markers: [[...]], TODO, TK, lorem
  - {{NAME}} greeting and {{UNSUB_URL}} present in both html and txt
  - the unsubscribe line is the last paragraph of the html
  - every <img> has alt text
  - redirect-wrapped links (google.com/url?q=...) that some mail tools insert
  - item count against email.max_items (counted as <strong> feature accents)
  - with --check-links: every http(s) URL returns 200

Exit code 1 if anything fails, so it can gate a send.
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import USER_AGENT, get, load_config  # noqa: E402

DASHES = re.compile("[\u2013\u2014]|&mdash;|&ndash;|&#8211;|&#8212;|&#x2013;|&#x2014;", re.I)


def check_url(url: str) -> str | None:
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return None if r.status == 200 else f"HTTP {r.status}"
    except urllib.error.HTTPError as ex:
        return f"HTTP {ex.code}"
    except Exception as ex:  # noqa: BLE001
        return str(ex)[:80]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("issue_dir")
    ap.add_argument("--check-links", action="store_true")
    ap.add_argument("--config")
    args = ap.parse_args()

    cfg = load_config(args.config)
    wd = Path(args.issue_dir)
    problems: list[str] = []
    files = {n: (wd / n).read_text() for n in ("email.html", "email.txt", "subject.txt", "social.md")
             if (wd / n).exists()}
    for n in ("email.html", "email.txt", "subject.txt"):
        if n not in files:
            problems.append(f"{n} missing")

    subject = files.get("subject.txt", "").strip()
    if subject:
        if re.search(r"changelog\s*#?\d+", subject, re.I):
            problems.append("subject reads like 'Changelog #N'; lead with the benefit instead")
        if len(subject) > 70:
            problems.append(f"subject is {len(subject)} chars; keep it under 70")

    banned = [p.lower() for p in (get(cfg, "voice.banned_phrases", []) or [])]
    for name, text in files.items():
        for i, line in enumerate(text.splitlines(), 1):
            if get(cfg, "voice.no_dashes", True) and DASHES.search(line):
                problems.append(f"{name}:{i} em or en dash")
            low = line.lower()
            for p in banned:
                if p in low:
                    problems.append(f"{name}:{i} banned phrase '{p}'")
            if re.search(r"\[\[|\bTODO\b|\bTK\b|lorem ipsum", line, re.I):
                problems.append(f"{name}:{i} leftover draft marker")
            if "google.com/url?" in line:
                problems.append(f"{name}:{i} redirect-wrapped link; use the real URL")

    html = files.get("email.html", "")
    txt = files.get("email.txt", "")
    for name, text in (("email.html", html), ("email.txt", txt)):
        if text and "{{NAME}}" not in text:
            problems.append(f"{name}: no {{{{NAME}}}} greeting")
        if text and "{{UNSUB_URL}}" not in text:
            problems.append(f"{name}: no {{{{UNSUB_URL}}}} unsubscribe link")
    paras = re.findall(r"<p\b[^>]*>(.*?)</p>", html, re.S | re.I)
    if paras and "{{UNSUB_URL}}" not in paras[-1]:
        problems.append("email.html: the unsubscribe line should be the last paragraph")
    for img in re.findall(r"<img\b[^>]*>", html, re.I):
        if not re.search(r'alt="[^"]+"', img):
            problems.append("email.html: an <img> has no alt text")
    max_items = int(get(cfg, "email.max_items", 5))
    accents = len(re.findall(r"<strong>", html, re.I))
    if accents > max_items + 2:
        problems.append(f"email.html: {accents} bold accents; that usually means too many items "
                        f"(max_items is {max_items}) or too much bolding")

    if args.check_links:
        urls = set()
        for text in files.values():
            urls |= set(re.findall(r"https?://[^\s\"'<>)]+", text))
        for u in sorted(urls):
            err = check_url(u)
            print(f"  {'OK  ' if not err else 'FAIL'} {u}{'' if not err else '  ' + err}")
            if err:
                problems.append(f"link {u}: {err}")

    if problems:
        print("\n".join(f"FAIL {p}" for p in problems))
        sys.exit(1)
    print("lint clean")


if __name__ == "__main__":
    main()
