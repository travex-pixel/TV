# TCL TV Transformation

Goal: make a slow, ad-heavy TCL Android/Google TV feel fast and minimal, with a
reversible debloat and a lightweight Apple-TV-inspired launcher.

Project rules (never broken): no factory reset, no root, no bootloader unlock,
no firmware flashing, no package uninstalls, no bulk debloat, every change
recorded with its original value and a rollback.

## Layout

| Path | Purpose |
|------|---------|
| `docs/01-discovery-and-environment.md` | Phase 1 report: environment audit, build toolchain, Partner Review 1 |
| `docs/ADB-SETUP.md` | How to enable ADB on the TV and connect from your computer |
| `tools/tv-discover.sh` | Read-only TV discovery script (macOS / Linux) |
| `tools/tv-discover.ps1` | Read-only TV discovery script (Windows PowerShell) |
| `tools/tvctl.py` | Backup, apply, restore (dry run), verify, screenshot and benchmark for the TV over adb; manifest-driven, device-identity checked |
| `profile/debloat-approved.txt` | The approved list actually applied (Tier 1 only) |
| `docs/05-approved-changes.md` | What was approved, declined, and applied, with rollback for each |
| `profile/debloat-proposed.txt` | The tiered package proposal for this TV (nothing applied without approval) |
| `docs/04-backup-and-debloat-proposal.md` | Backup/restore design, Partner Review 2 results, the Tier 1/2/3 proposal and the approval questions |
| `tools/match-profile.py` | Scores CleanYourTV's example lists against a discovery run (offline) |
| `docs/03-device-report.md` | The actual TV: TCL BeyondTV, Android TV 9, AP08; matched CleanYourTV profiles |
| `docs/02-cleanyourtv-review.md` | Capability comparison and security review of CleanYourTV; what is reused |
| `cleanyourtv/` | Vendored copy of [Gathin23/cleanyourtv](https://github.com/Gathin23/cleanyourtv) (MIT), pinned to the commit in `cleanyourtv-UPSTREAM-COMMIT.txt`, unmodified |
| `.github/workflows/build-launcher.yml` | Builds the launcher APK in GitHub Actions so no Android SDK is needed locally |

## Strategy

Reuse CleanYourTV (launcher, debloat tooling, restore) wherever it meets the
requirements; add only what is missing (full backup/manifest, photo
wallpapers, approval gates, performance measurement). The TV is never changed
without an explicit approval step.

## Current status

Phase 1 (discovery) is done: the TV is a TCL BeyondTV on Android TV 9 (AP08),
run from Termux on a phone. See `docs/03-device-report.md`. Phase 2/3 tooling is
written and tested on a simulated TV; see `docs/04-backup-and-debloat-proposal.md`
for the approval questions. Nothing has been changed on the TV.
