# Test results (real TV), Partner Review 5, performance comparison

TV: TCL BeyondTV, Android TV 9, AP08. Tests run 2026-10-23 00:34 to 01:05 TV time from Termux on
the owner's phone. Evidence: `backup/`, `bench/`, `shots/`, `backup/changes.json`.

## Test matrix

| # | Case | Result | Evidence |
|---|---|---|---|
| 1 | Baseline backup and manifest written | passed | `backup/manifest.json` (156 packages, serial, HOME) |
| 2 | Tier 1 apply (13 packages) | passed, 13/13 disabled | owner's terminal; `verify` after reboot shows 13 disabled, 0 drift |
| 3 | Animation scales 0.5 | passed | `changes.json` log, read back 0.5 |
| 4 | Private DNS AdGuard | passed; Netflix plays | owner check |
| 5 | Launcher install (sha256-checked) | passed | `changes.json` 00:53:22 "Success" |
| 6 | Theme push (config + 14 wallpapers) | passed | `changes.json` 00:53:50; screenshot shows dock and wallpaper |
| 7 | Launcher starts, no crash-buffer entries | passed | `shots/launcher-20261023-005359.png` |
| 8 | D-pad up/down/left/right, OK on each of 5 dock apps, Back | passed | owner check |
| 9 | Inputs pill, Settings pill, App library | passed | owner check |
| 10 | Home switch while stock launcher enabled | **failed as predicted**: "Success" but HOME still stock (priority 2 beats preference) | `changes.json` 00:57:36 |
| 11 | Stock launcher disabled (approved), Home set | passed, HOME = `com.gathin.tvhome` | `changes.json` 01:00:02-06 |
| 12 | Home button and Back-from-Netflix land on new launcher | passed | owner check |
| 13 | Reboot: Home comes back as the new launcher; disabled set unchanged | passed | `bench/after/bench.json` home field; `shots/after-reboot.png` |
| 14 | Wallpaper rotation after 30 min | **untested** (not enough elapsed time) | |
| 15 | Missing-app behaviour (dock app uninstalled) | untested on device; launcher skips missing dock apps by design | upstream tests |
| 16 | Offline operation | untested on device; launcher has no INTERNET permission, so it cannot depend on the network | manifest |
| 17 | HDMI picture with a source connected, tuner | untested (no source attached during the session) | |
| 18 | Remote Input/Source and Settings buttons after the switch | **awaiting owner confirmation** | |
| 19 | Standby/wake and multi-day stability | untested; `verify` is the ongoing check | |
| 20 | Restore on the real TV | **not exercised** (only on the simulated TV); dry run available at any time | docs/04 |

Skipped by decision: Tier 2 packages, voice stack, location permission grant, accessibility services.

## Partner Review 5 — Security and adversarial QA (independent pass over the real state)

- **Permissions**: the launcher declares network-state, Wi-Fi-state and fine-location. The
  location grant was deliberately never issued (`tvctl.py audit` prints the granted set to
  confirm). No INTERNET permission exists in the APK, verified with `aapt` on the CI build.
- **Network**: nothing in the launcher can reach the network. Private DNS sends every lookup to
  AdGuard; that is the owner's accepted trade-off and is reversible by one setting.
- **ADB exposure**: `ro.adb.secure=1`, so a new device must be approved on screen. Network
  debugging is still on; it is required until the project closes and must then be switched off
  (Developer options → USB debugging off, revoke authorisations). `tools/adb-closed.py` in the
  vendored repo confirms the port is closed from the phone.
- **Lockout**: the stock launcher is disabled, not removed. HOME candidates now are the new
  launcher (0), TCL's FallbackHome (-999) and Settings' FallbackHome (-1000). If the new
  launcher failed to start, TCL's fallback appears and Settings is reachable; from Settings →
  Apps the stock launcher can be re-enabled with the remote, with no ADB at all.
- **Fragile assumptions found**: the Home switch required the stock launcher to be disabled on
  this firmware, which the plan had treated as avoidable; it was caught by the tool's read-back,
  not by the command's "Success". `tvctl.py home` now documents this. Second: TCL re-enables
  `com.tcl.usercenter` at boot (it was running at 55 % CPU two minutes after the reboot); it is
  not in our list, so no drift, but it is why Tier 2c said it "barely sticks".
- **Package identification**: every disabled package matches a line with the same purpose in
  at least two sibling lists on the same board; none is a TV-input, remote, keyboard or
  updater package (the tool's protected set enforces this).
- **Recovery logic gap**: the real-TV restore has never been run. The simulated run passed, and
  the record holds exactly 14 package originals (13 Tier 1 + stock launcher), 5 settings, and
  the original HOME. Recommend one dry run on the real TV (`tvctl.py restore --dry-run`), which
  changes nothing, as the last verification step.
- **Severity summary**: no critical or high findings open. Medium: real restore unexercised
  (mitigated by dry run + TV-side re-enable path). Low: debugging left on until closure;
  `after-tier1.png` is empty (Netflix was on screen), superseded by later screenshots.

## Performance: before vs after

Conditions differ and that matters: "before" was measured after 16 days of uptime with the
stock launcher resident; "after" was measured **two minutes after a reboot**, while boot-time
services (Play services, TCL user center, swap reclaim) were still busy. CPU figures are
therefore not comparable; the app start times and memory are the fairer numbers.

| Measure | Before (stock home, 16 d uptime) | After (new home, 2 min after reboot) |
|---|---|---|
| Netflix cold start, 3 runs (ms) | 1091 / 806 / 994 | 769 / 670 / 641 |
| YouTube cold start, 3 runs (ms) | 1661 / 1528 / 1238 | 1083 / 925 / 882 |
| Memory available | 454 MB | 569 MB |
| Swap in use | 292 MB | 0 MB (fresh boot) |
| Idle CPU of the home app | stock launcher 34 % | new launcher not in top 25 |
| Processes | 262 | 273 (boot-time services still running) |
| Home cold start | not measurable (0 ms = already resident) | same |

Attribution, honestly: the start-time gain comes mostly from the stock launcher no longer
competing for CPU and memory (it alone used 34 % of a core at idle and 205 MB) and from the
fresh boot; the 13 disabled packages removed a handful of resident processes (bi ×2,
tclhome_passive, partnercustomizer, messagebox, tvrecommendations) but their CPU share was
small. The animation-scale change affects perceived snappiness, not these timings. A fair
"after" needs a re-run once the TV has been on for a day: `tvctl.py bench after-settled`.

## Partner Review 6 — Final release audit (CTO)

| Check | Status |
|---|---|
| Device compatibility | confirmed on the real unit; matches the AP08 field report |
| Backup completeness and gaps | package states, settings, HOME, props, screenshots in repo; app data and vendor partitions not backed up (documented, not needed since nothing is deleted) |
| Every change against approval | 13 Tier 1 (approved 1), scales (3), DNS (4), dock (5), wallpapers (6), launcher install (7), stock launcher disabled + Home switch (approved in chat after tests) |
| Reversibility | each change has its original in `changes.json`; restore order tested on a simulator; TV-side manual path exists |
| Restore script safety | identity check, dry run, protected set, never uninstalls |
| Build reproducibility | APK built by GitHub Actions from a pinned upstream commit; sha256 in repo; signature verified |
| Automated tests | upstream Python suite 206/206; launcher JVM tests run in CI; tvctl exercised on a simulated TV (13 + 5 scenarios) |
| Real-device results | 13 passed, 1 expected failure (handled), 6 untested as listed |
| Remote navigation | passed by owner |
| Reboot behaviour | passed |
| Launcher recovery | documented, not exercised on device |
| Performance evidence | measured; conditions caveated |
| Security and privacy | no network access in launcher; DNS trade-off accepted; debugging to be closed |
| Documentation | docs 01-08, README, RECOVERY |

Release decision: **approved for daily use**, with three follow-ups: run the restore dry run
once, re-measure after a day of uptime, and turn debugging off when you are done iterating.

## Appendix: final audit and restore dry run on the real TV (2026-10-23 01:11, 8 min after reboot)

`tvctl.py audit`:

```
launcher runtime permissions granted: ACCESS_NETWORK_STATE, ACCESS_WIFI_STATE   (no location)
launcher requests INTERNET: False
HOME: com.gathin.tvhome/.MainActivity
HOME candidates: com.gathin.tvhome/.MainActivity, com.tcl.keycustomfunctionservice/.FallbackHome,
                 com.android.tv.settings/.system.FallbackHome
private_dns_mode = hostname, private_dns_specifier = dns.adguard-dns.com
window/transition/animator animation scale = 0.5
enabled_accessibility_services = null
ro.adb.secure = 1, service.adb.tcp.port = 5555, adb_enabled = 1
disabled packages now: 34 (baseline 20)   -> 13 Tier 1 + the stock launcher
stock launcher state: disabled
crash buffer mentions of launcher: 0
load average: 19.47 at 8 min uptime
```

`tvctl.py restore --dry-run` listed, and would do, exactly: Home back to
`com.google.android.tvlauncher/.MainActivity`; `pm enable` for the 13 Tier 1 packages and the stock
launcher; delete `animator_duration_scale`, `private_dns_mode`, `private_dns_specifier`
(unset before); `transition_animation_scale` and `window_animation_scale` back to 1.0. Test case 20
therefore moves from "not exercised" to **dry run verified on device; live restore still unexercised**.

Note on the load average: it was 19.6 after 16 days of uptime before any change and 19.5 eight
minutes after the reboot with the new launcher. That number is a property of this firmware (kernel
threads counted as runnable), not something the project changed in either direction; the
responsive measures are the app start times and memory above.
