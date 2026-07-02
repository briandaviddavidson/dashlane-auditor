#!/usr/bin/env python3
"""Audit Dashlane vault for stale, weak, and reused passwords.

Reads credentials via the Dashlane CLI (`dcli password --output json`).
Passwords are inspected in memory only — they are never printed, logged,
or written to disk. The report contains site/login/date info only.

Usage:
    python3 audit.py [--days 365] [--markdown report.md]
"""

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone

DATE_FIELDS = [
    "modificationDatetime",
    "userModificationDatetime",
    "lastBackupTime",
    "creationDatetime",
]


def fetch_credentials():
    try:
        proc = subprocess.run(
            ["dcli", "password", "--output", "json"],
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError:
        sys.exit("dcli not found. Install with: brew install dashlane/tap/dashlane-cli")
    except subprocess.CalledProcessError as e:
        sys.exit(f"dcli failed (are you logged in? try `dcli sync`):\n{e.stderr}")
    return json.loads(proc.stdout)


def parse_timestamp(value):
    """Dashlane timestamps are unix seconds, sometimes as strings."""
    if value in (None, "", 0, "0"):
        return None
    try:
        ts = float(value)
    except (TypeError, ValueError):
        return None
    # Guard against milliseconds
    if ts > 1e12:
        ts /= 1000
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def last_changed(cred):
    for field in DATE_FIELDS:
        dt = parse_timestamp(cred.get(field))
        if dt:
            return dt, field
    return None, None


def password_strength_issues(password):
    issues = []
    if len(password) < 12:
        issues.append(f"short ({len(password)} chars)")
    classes = sum(
        any(f(c) for c in password)
        for f in (str.islower, str.isupper, str.isdigit)
    )
    if not any(not c.isalnum() for c in password):
        classes_total = classes
    else:
        classes_total = classes + 1
    if classes_total < 3:
        issues.append("low complexity")
    return issues


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=365,
                    help="flag passwords older than this many days (default 365)")
    ap.add_argument("--markdown", metavar="FILE",
                    help="also write the report as markdown (no passwords included)")
    args = ap.parse_args()

    creds = fetch_credentials()
    now = datetime.now(timezone.utc)

    # Detect reuse via in-memory hashes, then drop the passwords entirely.
    hash_counts = Counter()
    rows = []
    missing_dates = 0
    for cred in creds:
        password = cred.get("password") or ""
        pw_hash = hashlib.sha256(password.encode()).hexdigest() if password else None
        if pw_hash:
            hash_counts[pw_hash] += 1

        changed, date_field = last_changed(cred)
        if changed is None:
            missing_dates += 1

        rows.append({
            "title": cred.get("title") or cred.get("url") or "(untitled)",
            "url": cred.get("url") or "",
            "login": cred.get("email") or cred.get("login") or "",
            "changed": changed,
            "date_field": date_field,
            "age_days": (now - changed).days if changed else None,
            "pw_hash": pw_hash,
            "weak": password_strength_issues(password) if password else ["no password stored"],
        })
    del creds

    for row in rows:
        row["reused"] = bool(row["pw_hash"]) and hash_counts[row["pw_hash"]] > 1
        del row["pw_hash"]

    stale = sorted(
        (r for r in rows if r["age_days"] is not None and r["age_days"] > args.days),
        key=lambda r: -r["age_days"],
    )
    reused = [r for r in rows if r["reused"]]
    weak = [r for r in rows if r["weak"]]

    lines = []
    lines.append(f"# Dashlane password audit — {now.date()}")
    lines.append("")
    lines.append(f"Credentials scanned: {len(rows)}")
    lines.append(f"Older than {args.days} days: {len(stale)}")
    lines.append(f"Reused passwords: {len(reused)}")
    lines.append(f"Weak passwords: {len(weak)}")
    if missing_dates:
        lines.append(f"No usable date field: {missing_dates}")
    lines.append("")

    def section(title, items, extra=None):
        lines.append(f"## {title} ({len(items)})")
        lines.append("")
        if not items:
            lines.append("None.")
            lines.append("")
            return
        for r in items:
            age = f"{r['age_days']}d old" if r["age_days"] is not None else "age unknown"
            detail = extra(r) if extra else age
            lines.append(f"- **{r['title']}** — {r['login']} — {r['url']} — {detail}")
        lines.append("")

    section(f"Stale (>{args.days} days)", stale)
    section("Reused", reused,
            extra=lambda r: "same password as other entries")
    section("Weak", weak,
            extra=lambda r: ", ".join(r["weak"]))

    report = "\n".join(lines)
    print(report)
    if args.markdown:
        with open(args.markdown, "w") as f:
            f.write(report + "\n")
        print(f"\nWrote {args.markdown}", file=sys.stderr)


if __name__ == "__main__":
    main()
