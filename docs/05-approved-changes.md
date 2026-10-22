# Approved-change log

Approvals given by the owner on 2026-10-23 (chat). Every change below is applied only through
`tools/tvctl.py`, which records the original state in `backup/changes.json` before each command.

| # | Change | Decision | Rollback |
|---|---|---|---|
| 1 | Tier 1: disable 13 telemetry/promo/recommendation packages (`profile/debloat-approved.txt`) | **Approved, all 13** | `tvctl.py restore` (re-enables exactly those that were enabled before) |
| 2 | Tier 2 groups 2a-2d | **Declined** (nothing from Tier 2 is applied) | n/a |
| 3 | Animation scales window/transition/animator 1.0 → 0.5 | **Approved** | `tvctl.py restore`, or Developer options |
| 4 | Private DNS: `private_dns_specifier=dns.adguard-dns.com`, `private_dns_mode=hostname` | **Approved**, with the stated trade-off (resolver sees all DNS; no YouTube ad blocking) | `tvctl.py restore` puts both values back; emergency: `settings put global private_dns_mode opportunistic` |
| 5 | Dock: Netflix, YouTube, Disney+, Prime Video, Crunchyroll (in that order) | **Approved** | theme only, no TV state |
| 6 | Wallpapers: bundled illustrated `scenes` set for now | **Approved (option C)** | theme only |
| 7 | Install the launcher alongside the stock one (stock stays enabled, Home unchanged) | pending Phase 5 | uninstall the APK |
| 8 | Switch Home to the launcher | **not yet approved**; asked only after Phase 5 tests pass | `tvctl.py restore` sets Home back |

Status of each applied change is appended below as it happens, with the tool's output.

## Applied so far

| When (TV time) | Change | Result | Evidence |
|---|---|---|---|
| 2026-10-23 00:34 | Baseline backup | manifest written: 156 packages (20 disabled), HOME = stock launcher, serial recorded | `backup/20261023-003417/`, `backup/manifest.json`, home screenshot shows the Prime Video hero banner, "Mega Movie Week" promo row and recommendation chips |
| 2026-10-23 00:34 | Benchmark before | Netflix cold start 806-1091 ms, YouTube 1238-1661 ms, 454 MB available, 262 processes; `top` shows the **stock launcher at 34 % CPU while idle** | `bench/before/` |
| 2026-10-23 ~00:40 | Tier 1: 13 packages disabled | owner reports all 13 disabled (tool output not pasted; `changes.json` holds all 13 originals as `enabled`) | `backup/changes.json`; `verify` output to be captured with the next batch |
| same | Animation scales 0.5 ×3 | applied, read back 0.5 (originals: 1.0, 1.0, unset) | `backup/changes.json` log |
| same | Private DNS AdGuard, hostname mode | applied; owner confirms Netflix plays | `backup/changes.json` log |
| same | Screenshot after Tier 1 | **0 bytes** (Netflix was on screen; protected surface) — to be retaken with Home showing | `shots/after-tier1.png` |

Note: an early version of `tvctl.py apply` kept only the last package's log line (the recorded
original states were never affected). Fixed before the next batch; the per-package tool output
for the first batch exists only in the owner's terminal.
| 2026-10-23 00:53 | Launcher 2.5 installed (sha256 `3a62ce80…`), theme pushed, started | passed, owner tested D-pad, 5 dock apps, Inputs, Settings, App library | `changes.json`, `shots/launcher-20261023-005359.png` |
| 2026-10-23 00:57 | Home switch attempted with stock launcher enabled | not switched (priority 2 wins on this firmware) | `changes.json` |
| 2026-10-23 01:00 | **Stock launcher disabled** (approved after tests) and Home set to the new launcher | passed; Home and Back land on the new launcher | `changes.json` |
| 2026-10-23 01:03 | Reboot | new launcher is Home after restart; 13 packages still disabled, 0 drift | `bench/after/`, `shots/after-reboot.png` |
| 2026-10-23 | Wallpapers switched to 32-bit decode (`wallpaper_true_color`) to remove gradient banding | pushed; owner applied with `launcher theme` | `profile/theme/config.json` |
| 2026-10-23 | Photographic wallpapers | **declined for now** by the owner. Wikimedia Commons throttles this cloud address (HTTP 429, retry-after 600 s) and serves thumbnails from `thumb.wikimedia.org`, which was not allowed; the phone route (own photos into `profile/theme/photos`) remains available any time | n/a |
