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
  generate the new one — or pass `--assist` to let Playwright fill the form when
  a site recipe or generic detection works. At the end, the vault is re-synced
  and verification checks whether strength scores actually improved.

Fully unattended rotation isn't offered on purpose: every site's
change-password flow is different and most involve 2FA or CAPTCHAs, which is
why Dashlane retired its own Password Changer. This tool automates everything
around the one step that needs a human.

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

### Optional: Playwright assist mode

```sh
pip install -r requirements-optional.txt
playwright install chromium
```

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

## Releasing via Homebrew

The formula lives in `Formula/dashlane-auditor.rb`. To publish:

1. Push this repo to GitHub and tag a release: `git tag v0.5.0 && git push --tags`.
2. Compute the tarball checksum:
   `curl -sL https://github.com/briandaviddavidson/dashlane-auditor/archive/refs/tags/v0.5.0.tar.gz | shasum -a 256`
3. Fill in the `sha256` in the formula.
4. Create a tap repo named `homebrew-tap` on GitHub and copy
   `Formula/dashlane-auditor.rb` into its `Formula/` directory.

Then anyone can `brew tap briandaviddavidson/tap && brew install dashlane-auditor`.
