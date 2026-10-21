# Phase 1 — Discovery and environment audit

Date: 2026-10-21. Status: **environment audited; TV not yet inspected.**

Nothing on the television has been touched. No device facts below are
assumed: every "unknown" stays unknown until the discovery script has run on
the real TV.

## 1. Where this project runs

| Item | Finding |
|------|---------|
| Repository | `travex-pixel/tv`, branch `ccr-907b9d08-eg6d0w`, started empty |
| Environment | Claude Code **cloud container** (Ubuntu 24.04, x86_64, 4 CPU, 15 GB RAM, root) |
| Network | Container address is 192.0.2.2 (a non-routable test range). **No home-LAN access.** It cannot discover, ping, or `adb connect` to the TV. |
| Outbound | HTTPS through a policy proxy. Maven Central, Ubuntu apt, PyPI, GitHub reachable. **`dl.google.com` is denied** (HTTP 403 from the proxy). Google's Maven also redirects there, so the Android Gradle Plugin, Google's SDK packages and AndroidX libraries cannot be downloaded here. |
| Your computer | Operating system **unknown** (nothing in the repo or session tells me). Scripts are provided for both Windows (PowerShell) and macOS/Linux (bash). |

Consequence: **the physical TV can only be reached from a computer on the same
Wi-Fi as the TV.** This session can build the launcher, write and test the
scripts, and analyse everything you send back, but it cannot run ADB against
the TV itself. Everything that needs the TV runs through scripts you execute
locally, with results committed or pasted back.

## 2. Build toolchain (verified working in this container)

Because Google's SDK host is blocked, the normal Android Studio / Gradle route
is unavailable. A toolchain built from Ubuntu's own AOSP packages and Maven
Central was assembled and **proven end to end** with a throwaway hello-world
Android TV APK (compiled, dexed, aligned, signed, signature verified with
apksigner, badging shows `leanback-launchable-activity`, minSdk 28, targetSdk 34).

| Tool | Source | Version |
|------|--------|---------|
| `javac` | Ubuntu OpenJDK | 21 (compiling with `-source 8 -target 8`) |
| Android framework API jar (API 34) | Maven Central, `org.robolectric:android-all:14-robolectric-10818077`, SHA-1 verified | API 34 |
| `aapt2` (resources + manifest) | Ubuntu `aapt` / `android-sdk-build-tools` | AOSP 14 beta / 29.0.3 |
| `dx` (dex compiler) | Ubuntu `android-sdk-build-tools` | 29.0.3 (Java 8 bytecode only) |
| `zipalign`, `apksigner` | Ubuntu | 10.0 / 31.0.2 |
| `adb` | Ubuntu | 34.0.4 (usable only from your computer, not from here) |
| Gradle / Kotlin | preinstalled | 8.14.3 / 2.0.21 (not needed) |

Design consequence (and a good one): the launcher will be **pure Android
framework code, zero third-party libraries, zero AndroidX**. That is the
smallest, fastest, most auditable option and avoids the blocked dependency
host entirely. If you later allow `dl.google.com` in the environment's network
settings, Gradle and the official build tools become available too, but they
are not required.

Not available in the container: Android emulator (no KVM), screenshots of the
TV, any TV interaction. These are done on your side.

## 3. What is known about the TV

Nothing is confirmed yet. From your description: TCL brand, Android/Google TV
newer than version 9, slow, ad-heavy. Model, exact OS version, SDK level,
firmware, hardware, launcher and package inventory are all **unknown**. The
discovery script collects all of these read-only.

## 4. Compatibility assessment (what depends on the real TV)

These are the firmware-dependent questions the discovery output will answer.
Nothing is decided until then.

| Question | Why it matters | How discovery answers it |
|----------|----------------|--------------------------|
| Android version and SDK (11/12/14?) | Package disabling, settings, HOME-role behaviour all changed between versions | `ro.build.version.*` |
| Google TV vs classic Android TV launcher | Google TV (`com.google.android.apps.tv.launcherx`) and TCL's own home differ in where ads come from | HOME resolution + package list |
| Can the HOME role be changed without root? | Many Android TV builds have **no "default launcher" chooser**. Android 10+ uses the HOME role; some TV builds pin it. If pinned, a third-party launcher can only be a "launch-on-demand" home (e.g. opened by a button/app), not the Home-button target. **We will not bypass that.** | `cmd role get-role-holders android.app.role.HOME`, HOME candidates list, and later a controlled test |
| Does `pm disable-user` work from ADB shell on this firmware? | It is the only reversible, non-root way to switch off vendor components. Some firmware restricts it for system packages. | Tested later on one low-risk package, only after your approval |
| Which packages actually serve the ads/recommendations? | TCL feeds, Google TV "For you" row, and in-app ads are three different things with three different remedies | Package inventory + screenshot + per-package review |
| Can screenshots be captured? | For honest before/after evidence | `screencap` attempt in the script |
| Can settings be read and written over ADB? | Animation scales etc. are the first safe speed-ups | `settings list` output |

What **cannot** be promised regardless of firmware:
- Ads inside Netflix, YouTube, Prime, etc. are served by those apps. No
  launcher or debloat changes them.
- Google TV's own home-row promotions can be reduced through the TV's own
  settings and by not using that launcher, but not deleted.
- Deep CPU/RAM limits of a budget TV. We can reduce what competes for them.

## 5. Backup and recovery feasibility

- **Possible from ADB without root:** full package inventory with APK paths,
  enabled/disabled state per package, all three `settings` namespaces, system
  properties, APK copies of most apps (`adb pull` of the base APK is usually
  allowed for system apps; some firmware blocks pulling from `/data/app`),
  screenshots, logs.
- **Not possible without root:** app private data, Google account state,
  vendor configuration inside protected partitions, a full image. The
  original TCL/Google launcher is never removed, so its data never needs
  restoring.
- **Recovery path that does not depend on our launcher:** the original
  launcher stays installed and enabled throughout. If our app misbehaves, the
  Home button still resolves to the original (if we never switched the HOME
  role) or `adb shell` can re-enable/re-set it via the manifest-driven restore
  script. An ADB connection is the only hard requirement for recovery, which
  is why the ADB setup guide includes reconnecting instructions.

## 6. Partner Review 1 — Principal Android Engineer

Independent challenge of the above:

1. **"You have no TV access; is anything you've done real?"** Correct that
   nothing about the TV is known. What is real: the build pipeline works
   (APK built and signature-verified), and the discovery scripts are
   read-only and were tested for their failure path. The plan does not depend
   on any guess about the firmware.
2. **"Using Robolectric's `android-all` jar as the compile classpath is
   unusual."** It is a complete framework jar for API 34 and is only used at
   compile time; the APK contains none of it. Risk: it exposes hidden/internal
   APIs that a stock `android.jar` would hide. Mitigation: a lint step will
   flag any use of non-public packages, and the code will stick to documented
   `android.*` APIs only. If `dl.google.com` is later allowed, the official
   `android.jar` replaces it with no code change.
3. **"`dx` instead of `d8` means no Java 8 language desugaring."** True: no
   lambdas or default methods. Acceptable for a small launcher written in
   plain Java 8-compatible style; the build will fail loudly if violated.
4. **"Will a third-party launcher even take the Home button on a TCL Google
   TV?"** Unknown, and this is the biggest risk to the headline goal.
   Reports vary by firmware: some TCL Google TV builds offer no launcher
   chooser, and the Home button always returns to Google TV's home. The plan
   therefore delivers the launcher as a **standalone home experience first**
   and treats the Home-button switch as a separate, firmware-gated step with
   its own approval and rollback. This is checked, not assumed.
5. **"Package disabling may be blocked on newer firmware."** Also unknown.
   The approach is to probe with one approved, low-value package and record
   the exact result before proposing a list.
6. **"The user is not a developer; two scripts plus platform-tools is a lot."**
   It is the minimum: ADB cannot be avoided for a non-root, reversible
   approach, and Google's platform-tools is a single zip with no installer.
   The guide is written for that.

Verdict: the approach is credible and the risks are named. Proceed to running
discovery on the TV. No changes to the TV are proposed yet.

## 7. Next safe step (you)

1. Follow `docs/ADB-SETUP.md` to turn on debugging on the TV and install
   platform-tools on your computer.
2. With the **TV's home screen showing** (so the screenshot captures the
   current ads/promotions), run from the repository folder:
   - Windows PowerShell: `.\tools\tv-discover.ps1 -Target <TV-IP>`
   - macOS/Linux: `./tools/tv-discover.sh <TV-IP>`
3. Paste `discovery/latest-summary.txt` into the chat, or commit and push the
   whole `discovery/` folder. The full folder (package lists and screenshot)
   is what Phases 2 and 3 need.

The script is read-only. Nothing is changed, disabled or installed.
