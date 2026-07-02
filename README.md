# dashlane-updater

Semi-automated Dashlane password rotation.

1. **Audit** — `audit.py` reads the vault via the Dashlane CLI and reports
   stale, reused, and weak passwords. Passwords are compared in memory only
   and never printed or written to disk.
2. **Rotate** — for each flagged credential, browser automation drives the
   change-password flow on the site while the Dashlane browser extension
   captures the updated password back into the vault. Human stays in the
   loop for 2FA, CAPTCHAs, and save confirmation.

## Setup

```sh
brew install dashlane/tap/dashlane-cli
dcli sync   # interactive: registers this device and logs in
```

## Usage

```sh
python3 audit.py                          # report to stdout
python3 audit.py --days 180               # custom staleness threshold
python3 audit.py --markdown report.md     # also write markdown report
```

`report.md` and other generated reports are gitignored — they contain
site/login metadata you probably don't want in git history.
