# Phase 1c — Device report: your TCL TV

Date: 2026-10-23. Source: `tools/tv-discover.sh` run from Termux on your phone against the TV
(summary pasted into the session; the full folder is to be committed from the phone). Read-only;
nothing on the TV was changed.

## Identity

| Field | Value |
|---|---|
| Brand / model / device / product | TCL / `BeyondTV` / `BeyondTV` / `BeyondTV` (TCL's platform name; the retail model number is on the back-panel label, not in software) |
| Android | **Android TV 9**, SDK 28 (not newer than 9, as first assumed) |
| Build | `PPR1.180610.011`, incremental **AP08**, security patch 2021-01-05 |
| Fingerprint | `TCL/BeyondTV/BeyondTV:9/PPR1.180610.011/AP08:user/release-keys` |
| TCL software | `V8-R851T02-LF1V634` |
| Board / SoC | Realtek `rtd285o` (RTD2851 family), 4 × ARMv7 cores, **32-bit** (armeabi-v7a) |
| RAM | 2 GB total, **430 MB available** at the time of the run |
| Storage | 10 GB data partition, 6.4 GB used, 3.5 GB free |
| Display | 1920 × 1080, density 320 |
| Home launcher | `com.google.android.tvlauncher/.MainActivity` (classic Android TV Home, priority 2). The only other HOME claimants are the two fallback stubs (`com.tcl.keycustomfunctionservice/.FallbackHome`, `com.android.tv.settings/.system.FallbackHome`). **No Google TV setup wizard claims HOME.** |
| Saved Wi-Fi owner | `android.uid.system` (not the setup wizard), so disabling nothing here can drop the Wi-Fi |
| TV input providers | `com.tcl.tvinput` (tuner + HDMI pass-through), `com.google.android.videos` |
| ADB | authorised, `ro.adb.secure=1` (the TV asks before trusting a device), shell uid 2000 with the normal restrictions |
| Packages | 156 total, 139 system, 17 user-installed, 20 already disabled at the factory or earlier |
| Screenshot | captured successfully (215 KB), so before/after evidence is possible |
| Settings | global, system and secure namespaces all readable; animation scales currently 1.0 |

## What was running

Netflix (136 MB) and the stock launcher (136 MB) were the two largest processes, then system,
Play Services, Play Store, the two Google voice processes (katniss, 68 MB together), TV Settings,
and Chromecast (mediashell). 261 processes in all.

## Compatibility: this is the best-covered TCL family in CleanYourTV

`tools/match-profile.py` ranks the matching lists; the top ones share this exact board, build
number and Android version:

| Profile | Firmware | Relationship to this TV |
|---|---|---|
| `docs/devices/tcl-beyondtv-ap08.md` | BeyondTV, **AP08**, patch 2021-01-05, 2 GB | **Same build and patch.** Field report: launcher installed, set as Home, survived a restart; remote buttons, casting and HDMI menu confirmed by the owner |
| `examples/tcl-beyondtv2-latin-america` | fingerprint `...AP08:user/release-keys`, LF1V660 | Same fingerprint, different region software; very conservative 2-package list with a 24-check smoke test |
| `examples/tcl-beyondtv-rt2851` | AP06, LF1V606 | Same board, one build older; 27-package list with a detailed keep/do-not-disable table and quirks |
| `examples/tcl-55c715` | AP06, LF1V606 | Same board; 33-package list, in daily family use, includes memory measurements (557 MB → ~780 MB available) |
| `examples/tcl-beyondtv-pl` | AP03 | Same board, older build |
| `examples/tcl-beyondtv` | India AP build | Same build number, different region preloads; 12-package conservative list |

What this means for each goal:

- **Launcher replacement: expected to work fully**, including the Home button. On Android TV 9
  the HOME switch is `cmd package set-home-activity`, there is no setup-wizard trap, and the
  AP08 report confirms the switch survives a reboot. The launcher's minimum is SDK 26; this TV
  is 28. 32-bit CPU is fine (plain Java, no native code).
- **Package disabling: works** (`pm disable-user` succeeded on all sibling units). Two quirks
  are documented for this firmware and will be checked on yours: `com.tcl.usercenter` and
  `com.tcl.notereminder` are re-enabled by TCL at every boot, and `com.tcl.esticker` came back
  by itself on one AP08 unit.
- **Where the ads come from on this TV:** three sources, two of them removable.
  `com.tcl.tv.tclhome_passive` and `com.tcl.partnercustomizer` push TCL promo rows into the
  stock home; `com.google.android.tvrecommendations` and
  `...leanbacklauncher.recommendations` feed the stock home's recommendation rows. Both sets
  become irrelevant once our launcher is Home, and can be disabled on top for less background
  work. Ads inside Netflix, YouTube and the like are untouched by any of this.
- **Performance:** the firmware family is known for the voice stack (`voice_ap` and
  `katniss:interactor`) burning 25 to 45 % of one core continuously; on the C715 switching the
  Google voice packages off freed about 220 MB and most of that CPU. That costs the remote's
  microphone button and typed search on the stock home, so it is your choice, not a default.
- **Firmware updates:** `com.tcl.versionUpdateApp` is TCL's updater. We keep it enabled unless
  you say otherwise.
- **Memory headroom is the real constraint.** 430 MB available of 2 GB with Netflix and the
  stock launcher resident. The launcher's 1 GB-TV design (RGB_565 wallpapers, no blur, no
  services) is the right fit; wallpapers will be pre-sized to 1920 × 1080.

## Known limits on this firmware (from the sibling reports)

- Screenshots over HDMI and inside Netflix come back blank (protected content). Home first.
- The remote's Source button goes through TCL's own path; the launcher's Inputs menu works
  through the Android TV input framework and listed HDMI 1, HDMI 2, AV and Live TV on the AP08 unit.
- `cmd role` does not exist on Android 9 (seen in the summary); the HOME preference is set per
  activity instead, which the tooling already handles.
- The clock on one sibling ran hours fast because of a stale time sync; worth checking on yours.

## Next

1. Commit the full `discovery/` folder from the phone (package lists, settings, screenshot).
2. Phase 2: backup and manifest from that folder; restore tooling pre-check.
3. Phase 3: the package list, built from the AP08 report and the RT2851/C715 lists, reviewed
   with you line by line in three tiers before anything is applied.
