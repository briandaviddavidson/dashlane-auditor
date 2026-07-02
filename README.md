# dashlane-auditor

Audit and rotate stale Dashlane passwords, semi-automatically.

- **`dashlane-auditor audit`** — reads your vault via the Dashlane CLI and
  writes a markdown report (`dashlane-audit.md`) of stale, reused, and weak
  passwords, each with a direct change-password link. Weakness uses Dashlane's
  own 0–100 strength score where available. Entries unused for `--dead-days`
  (default 730) go in a separate "likely dead accounts" section with the
  suggestion to close the account rather than rotate it. Passwords are
  compared in memory only and never printed or written to disk.
- **`dashlane-auditor fix`** — walks through the flagged credentials one at a
  time, most-recently/heavily used first so the accounts that matter get
  rotated first: generates a strong password to your clipboard, opens the site's
  change-password page (using the `/.well-known/change-password` convention),
  waits for you to complete the change (2FA, CAPTCHAs, and the Dashlane
  extension's save prompt), then re-syncs the vault to verify each entry was
  actually updated. The clipboard is cleared when the run ends.

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

## Setup

```sh
dcli sync   # interactive: registers this device and logs in (needs a real terminal)
```

## Usage

```sh
dashlane-auditor audit                 # report to dashlane-audit.md + stdout
dashlane-auditor audit --days 180      # custom staleness threshold
dashlane-auditor fix                   # interactive rotation assembly line
```

Generated reports are gitignored — they contain site/login metadata you
probably don't want in git history.

## Releasing via Homebrew

The formula lives in `Formula/dashlane-auditor.rb`. To publish:

1. Push this repo to GitHub and tag a release: `git tag v0.2.0 && git push --tags`.
2. Compute the tarball checksum:
   `curl -sL https://github.com/briandaviddavidson/dashlane-auditor/archive/refs/tags/v0.2.0.tar.gz | shasum -a 256`
3. Fill in the `sha256` in the formula.
4. Create a tap repo named `homebrew-tap` on GitHub and copy
   `Formula/dashlane-auditor.rb` into its `Formula/` directory.

Then anyone can `brew tap briandaviddavidson/tap && brew install dashlane-auditor`.
