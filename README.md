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

## Current status

Phase 1 (discovery) is in progress. The cloud environment cannot see the TV,
so the discovery script must be run on a computer on the same Wi-Fi as the TV.
See `docs/01-discovery-and-environment.md` for the next step.
