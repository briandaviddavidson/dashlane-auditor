# dashlane-auditor

Audit and rotate stale Dashlane passwords, semi-automatically.

- **`dashlane-auditor audit`** — reads your vault via the Dashlane CLI and
  writes a report of passwords needing rotation (markdown or JSON).
  Rotation is evidence-based (NIST 800-63B): a password is flagged if it is
  **breached** (checked against HaveIBeenPwned's range API — k-anonymity, only
  5-char SHA-1 prefixes ever leave your machine; skip with `--no-breach-check`),
  **reused** across entries, or **weak** (Dashlane's own 0–100 strength score).
  Old-but-strong-and-unique passwords are reported as stale but need no action.
  Entries unused for `--dead-days` (default 730) go in a separate "likely dead
  accounts" section with the suggestion to close the account rather than rotate
  it. Passwords are compared in memory only and never printed or written to
  disk.
- **`dashlane-auditor fix`** — walks through the flagged credentials one at a
  time, most-recently/heavily used first. Opens each site's change-password page
  (using a bundled URL database, the `/.well-known/change-password` convention,
  or the site origin as fallback) and tracks your progress with automatic resume.
  On each page, use the Dashlane extension to fill the current password and
  generate the new one — or pass `--assist` (experimental) to let Playwright
  fill the form when a site recipe or generic detection works. At the end, the
  vault is re-synced and verification checks whether strength scores actually
  improved.

Fully unattended rotation isn't offered on purpose: every site's
change-password flow is different and most involve 2FA or CAPTCHAs, which is
why Dashlane retired its own Password Changer. This tool automates everything
around the one step that needs a human.

## Sample report

Generated from the test fixture (`tests/test_auditor.py`), not a real vault:

```markdown
# Dashlane password audit — 2026-10-10

Credentials scanned: **7**

- Needing rotation: **3**
  - of which found in known breaches: **1**
- Likely dead accounts: **1** (unused for 730+ days)
- Stale but strong & unique: **1** — no action needed; modern guidance (NIST 800-63B) says rotate on evidence, not age

## Rotate these

| # | Site | Login | Last used | Problem | Change password |
|---|------|-------|-----------|---------|-----------------|
| 1 | google.com | you@example.com | 2026-10-09 (1d ago) | password reused on other accounts | [open](https://myaccount.google.com/security) |
| 2 | amazon.com | you@example.com | 2026-10-09 (1d ago) | in known breaches (1,821,507× seen); weak: Dashlane strength 10/100 | [open](https://www.amazon.com/ap/cnep) |
| 3 | reddit.com | you@example.com | 2026-10-05 (5d ago) | password reused on other accounts | [open](https://www.reddit.com/settings/account) |

## Likely dead accounts — consider deleting the account instead

| # | Site | Login | Last used | Times used | Breached? | Reused? |
|---|------|-------|-----------|------------|-----------|---------|
| 1 | netflix.com | you@example.com | 2024-01-14 (1000d ago) | 10 |  |  |
```

## Install

```sh
brew tap briandaviddavidson/tap
brew install dashlane-auditor
```

Or from a checkout:

```sh
brew install dashlane/tap/dashlane-cli
ln -s "$PWD/dashlane-auditor" /usr/local/bin/dashlane-auditor
```

### Optional: Playwright assist mode (experimental)

```sh
pip install -r requirements-optional.txt
playwright install chromium
```

With `--assist`, the tool fills the change-password form with a generated
password and submits it. Because the site is now using a password your vault
doesn't have yet, it then:

1. asks you, with the browser still open, whether the site accepted the change
   (if not, nothing changed and you fall back to the manual flow);
2. puts the new password on your clipboard, without printing it, and asks you to
   paste it into the Dashlane entry;
3. re-syncs the vault and won't move on until that entry matches, then clears
   the clipboard.

Assist only fills passwords on the site it meant to open. If the page
redirects to another domain, it stops and falls back to the manual flow. To
reuse your Chrome logins with `--profile`, quit Chrome first; Playwright can't
open a profile that's already in use.

## Setup

```sh
dcli sync   # interactive: registers this device and logs in (needs a real terminal)
```

## Usage

```sh
# Audit
dashlane-auditor audit                              # markdown report
dashlane-auditor audit --format json                # machine-readable output
dashlane-auditor audit --only weak                  # weak passwords only
dashlane-auditor audit --days 180

# Fix (interactive rotation)
dashlane-auditor fix                                  # all flagged credentials
dashlane-auditor fix --only weak                    # weak passwords only
dashlane-auditor fix --only weak --assist           # Playwright-assisted forms
dashlane-auditor fix --only weak --assist \
  --profile "$HOME/Library/Application Support/Google/Chrome"  # reuse Chrome logins
```

Progress is saved automatically to `~/.dashlane-auditor/progress.json` so you
can quit mid-session and pick up later. Use `--no-resume` to start fresh.

### Custom site URLs and recipes

Override or extend change-password URLs:

```sh
mkdir -p ~/.dashlane-auditor
cp sites.json ~/.dashlane-auditor/sites.json   # edit to add domains
```

Add per-site Playwright recipes (YAML) for reliable automation:

```sh
mkdir -p ~/.dashlane-auditor/sites
cp sites/github.com.yaml ~/.dashlane-auditor/sites/
```

See `sites/github.com.yaml` for the recipe format.

Generated reports are gitignored — they contain site/login metadata you
probably don't want in git history.

## Development

Tests use only the standard library. A fake `dcli` serves a fixture vault and
HaveIBeenPwned calls are stubbed, so nothing touches a real vault or the network:

```sh
python3 -m unittest discover -v tests
```

CI runs the same suite on macOS and Ubuntu with Python 3.10 and 3.13.

## Releasing via Homebrew

The formula lives in `Formula/dashlane-auditor.rb`. To publish:

1. Push this repo to GitHub and tag a release: `git tag v0.5.0 && git push --tags`.
2. Compute the tarball checksum:
   `curl -sL https://github.com/briandaviddavidson/dashlane-auditor/archive/refs/tags/v0.5.0.tar.gz | shasum -a 256`
3. Fill in the `sha256` in the formula.
4. Copy `Formula/dashlane-auditor.rb` into the `Formula/` directory of the
   [`briandaviddavidson/homebrew-tap`](https://github.com/briandaviddavidson/homebrew-tap)
   repo and push.

Then anyone can `brew tap briandaviddavidson/tap && brew install dashlane-auditor`.
