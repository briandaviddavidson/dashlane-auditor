# dashlane-updater

Audit and rotate stale Dashlane passwords, semi-automatically.

- **`dashlane-updater audit`** — reads your vault via the Dashlane CLI and
  writes a markdown report (`dashlane-audit.md`) of stale, reused, and weak
  passwords, each with a direct change-password link. Passwords are compared
  in memory only and never printed or written to disk.
- **`dashlane-updater fix`** — walks through the flagged credentials one at a
  time: generates a strong password to your clipboard, opens the site's
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
brew tap YOURUSER/tap
brew install dashlane-updater
```

Or from a checkout:

```sh
brew install dashlane/tap/dashlane-cli
ln -s "$PWD/dashlane-updater" /usr/local/bin/dashlane-updater
```

## Setup

```sh
dcli sync   # interactive: registers this device and logs in (needs a real terminal)
```

## Usage

```sh
dashlane-updater audit                 # report to dashlane-audit.md + stdout
dashlane-updater audit --days 180      # custom staleness threshold
dashlane-updater fix                   # interactive rotation assembly line
```

Generated reports are gitignored — they contain site/login metadata you
probably don't want in git history.

## Releasing via Homebrew

The formula lives in `Formula/dashlane-updater.rb`. To publish:

1. Push this repo to GitHub and tag a release: `git tag v0.1.0 && git push --tags`.
2. Compute the tarball checksum:
   `curl -sL https://github.com/YOURUSER/dashlane-updater/archive/refs/tags/v0.1.0.tar.gz | shasum -a 256`
3. Fill in `YOURUSER` and the `sha256` in the formula.
4. Create a tap repo named `homebrew-tap` on GitHub and copy
   `Formula/dashlane-updater.rb` into its `Formula/` directory.

Then anyone can `brew tap YOURUSER/tap && brew install dashlane-updater`.
