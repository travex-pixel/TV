# Phase 1b — CleanYourTV: what it provides, what it lacks, and whether to trust it

Date: 2026-10-21. Reviewed: `Gathin23/cleanyourtv` at commit
`7be231abd065fc3a573f8eb56335d9263415d0e7` (1,036 commits, MIT licence), now vendored
unchanged under `cleanyourtv/` in this repository and pinned to that commit.
**Nothing was run against the TV. The TV is still uninspected.**

## 1. Verdict in one paragraph

CleanYourTV is a mature, well-guarded implementation of almost exactly this project: ADB-only,
no root, `pm disable-user` only (never uninstall), a recorded pre-change state with a replayable
restore, an Apple-TV-style native launcher with a dock, app library, clock, wallpaper rotation
and an in-launcher wallpaper picker, plus 40 TCL-specific package lists and three TCL field
reports. Reusing it removes the launcher build, the debloat tooling and most of the restore
tooling from this project's scope. What it does not provide: photographic nature wallpapers (its
"scenes" are code-drawn illustrations), a full-state backup beyond the packages it touches, a
device-identity check in restore, performance measurement, and a workflow that waits for your
approval before the stock launcher is disabled. All of those are small additions, not rewrites.

## 2. Requirement-by-requirement comparison

| Your requirement | CleanYourTV status | What we do |
|---|---|---|
| Never factory reset / root / flash / uninstall | **Met.** `pm disable-user --user 0` only; the scripts refuse any list entry that is not a bare package name | Reuse |
| No bulk debloat, individual approval | **Partly.** Lists are applied as a batch by `tools/disable.sh`; the project's own prompt says to disable in small batches with screenshots between | We review every line of the matching list with you first, then apply in small approved batches |
| Record original state + reversal method | **Met for what it changes.** `tools/recovery.py --save` records each listed package's state (enabled / disabled / absent), the Home owner and the 3 animation scales *before* the first command, and refuses to overwrite a record on retry | Reuse, and add a copy of the record to the repo backup folder |
| Full backup (inventory, APK paths, all settings, getprop, screenshots, manifest) | **Not provided** (its prompt asks the assistant to do it ad hoc) | Our `tools/tv-discover.*` already captures all of this read-only; it becomes the baseline backup |
| Restore script with dry run, device check, manifest-driven | **Mostly met.** `recovery.py --commands <list>` prints the exact restore commands without running them (that is the dry run); `restore.sh` pipes them to the TV. Replays recorded states, leaves already-disabled packages alone, puts Home back to the recorded component. **Gap:** identifies the TV only by IP address, no fingerprint/serial check; a changed IP means "no record" and a fallback that re-enables the whole list (it warns loudly) | Reuse; add a small pre-check that compares `ro.build.fingerprint` and serial against the backup before restore runs; give the TV a fixed IP |
| Never disable the original launcher before the replacement is proven, and ask first | **Not the default.** `launcher/build-and-install.sh` installs, starts the new launcher, verifies `Status: ok`, then disables the stock launcher and sets Home in the same run (with automatic rollback if Home does not land on it). `STOCK_LAUNCHER=none` installs without touching Home | Phase 5 runs it with `STOCK_LAUNCHER=none`. The Home switch is a separate, approved step later |
| Apple-TV-style launcher: dark, cinematic, big type, dock, app library, clock/date, settings, wallpaper picker, focus memory | **Met.** Pitch-black UI, glass focus highlight, dock row of your chosen apps, optional app library, greeting + large thin clock + date (Outfit font, OFL licence), on-TV Launcher settings, wallpaper picker in those settings, remembers the last focused tile, deterministic D-pad rules. 429 KB installed, plain Java + AndroidX RecyclerView, CI rejects builds over 440 KB | Reuse unchanged; configure via a theme (no rebuild) |
| Cinematic **nature photography** wallpapers, licensed, local, rotating, light on RAM, graceful fallback, manual selection | **Half met.** Rotation engine is exactly what you asked for: local files only, background decode after the first image, RGB_565 by default (4 MB at 1080p), skips unreadable files, no video, no network, interval and shuffle/sequential configurable, picker in settings. The shipped `themes/scenes` images are **illustrations drawn by a script**, not photographs; `aurora`/`dussehra` are single images | Keep the engine; add our own theme folder with CC0/public-domain photographs resized to the TV's resolution (see §6, this needs one decision from you) |
| No ads, tracking, account, backend in the launcher | **Met.** No `INTERNET` permission at all, so the app cannot reach the network. `allowBackup=false` | Reuse |
| Remote-control UX incl. Input button after the stock launcher is gone | **Met.** Optional accessibility services (off by default) restore the Input and app buttons that only the stock Google TV launcher answered | Enable only if needed on your firmware, after the Home switch |
| Reliable recovery that does not depend on the custom launcher | **Met.** Restore works over ADB regardless of the launcher's state; the install script writes a local recovery-commands file when a handover fails mid-way | Reuse |
| Reconnect-to-ADB instructions, close ADB afterwards | **Met.** README + `tools/adb-closed.py` verifies port 5555 is closed | Reuse |
| Screenshots from the real TV | **Met.** `tools/tv.py --screenshot` (captures on the TV, pulls the PNG; reports 0-byte captures on HDMI/Live TV honestly) | Reuse |
| Performance before/after measurement | **Not provided** (`show_stats` shows CPU/RAM on screen, that is all) | Small script in Phase 6 (`am start -W` timings, meminfo, process counts) |
| Firmware-update drift | **Bonus.** `tools/check.py` reports what an update re-enabled; `--fix` reapplies the list | Reuse |
| Ads inside Netflix/YouTube | **Not possible**, and the project says so. Optional Private DNS (AdGuard) blocks ad/tracker domains system-wide but not YouTube ads, and that resolver then sees all DNS | Offer as an opt-in with the trade-off stated |

## 3. Compatibility with your TCL TV

Unknown until discovery runs, but the odds are good. The project carries **40 TCL lists** across
Android TV 9/11 and Google TV 11/12/14, plus field reports for a G08 (QM7), a G03 (75C63B) and the
China MT9655. The decisive identifiers are `ro.product.device` / `ro.product.name` (for example
`G08` / `G08_4K_GB`) and the build (`AU02`, `AR20`...), **not** the retail model or
`ro.product.model`, which is `Smart TV Pro` on many unrelated TCL sets.
`tools/match-profile.py discovery/<run>` scores every list against your getprop output.

Three firmware-dependent facts decide how far we can go, and the discovery script now records
all three:

1. **Who owns the saved Wi-Fi network.** On many Google TV sets it is the setup wizard
   (`setupwraith`); disabling the wizard then deletes the network and takes the TV off Wi-Fi.
   The fix is to forget and re-join the network first. `disable.sh` refuses to disable the wizard
   while it owns the network.
2. **Whether the setup wizard claims Home after the stock launcher is disabled.** On most Google
   TV sets it does, via a `RecoveryActivity` that the shell cannot disable on its own, so the whole
   wizard package has to be disabled for a third-party launcher to own Home. On one TCL (G05) that
   does not survive a reboot, so the launcher half is "debloat only" there. This is exactly the
   "do not assume the Home switch works" risk from Phase 1, now with named precedents.
3. **Whether sideloading is allowed at all.** China-market TCL firmware refuses every APK; the
   discovery script reads TCL's install-policy row to detect this before anything is built.

## 4. Security and recovery review of the scripts (Partner Review 1b)

Reviewed line by line: `tools/tv.py`, `disable.sh`, `disable.ps1` (guard parity confirmed),
`restore.sh`, `recovery.py`, `b64push.py`, `theme.sh`, `check.py`, `launcher/build-and-install.sh`,
the launcher manifest, build config, and the wallpaper code. Its own 206-test Python suite was
run here: **206 passed, 1 skipped, 0 failed.**

Sound:
- Every package name from a list or from the TV is validated against a strict regex before it is
  pasted into a shell command, so a malicious list cannot inject commands. Remote paths in
  `b64push.py` are likewise restricted; pushed files are md5-verified and moved into place atomically.
- `disable.sh` writes the recovery record to disk *before* the first command reaches the TV, and
  stops if that write fails. Three guards: the Wi-Fi-owner check above, a Home guard (never
  disables the only Home owner, and does not count the wizard, Settings or TCL's `FallbackHome`
  as usable homes), and a TV-input guard (never disables a package that asks for
  `TV_INPUT_HARDWARE`, since that kills HDMI picture until a full restore and cold boot).
- The launcher requests no `INTERNET` permission; its two accessibility services and the
  screensaver are opt-in; the theme content provider is exported but gated behind
  `WRITE_SECURE_SETTINGS`, which only the ADB shell and system hold. No third-party analytics.
- The ADB private key `tools/tv.py` generates is stored 0600; it reuses your existing
  `~/.android/adbkey` if present so the TV only asks to authorise one key.

Concerns, each with the mitigation we will apply:
- **The install script disables the stock launcher by default** (above). We always run it with
  `STOCK_LAUNCHER=none` until you approve the switch.
- **The install script grants `ACCESS_FINE_LOCATION`** to the launcher via `pm grant`, needed only
  to display the Wi-Fi network name. If you would rather not, we set `show_network_pill` false in
  the theme and revoke the grant with `pm revoke`. Your call, low stakes either way.
- **Restore identifies the TV by IP only.** We add a fingerprint/serial pre-check and keep a copy
  of the recovery record in the repo's backup folder (upstream keeps it in `~/.cleanyourtv/`).
- **Restore does not undo Private DNS** if we enable it. Recorded separately in our manifest.
- **`com.tcl.ttvs`** appears in several TCL lists as analytics/ACR but on some sets is also the
  firmware updater. Treated as "optional, with trade-offs" and verified on your set first.
- **Festival skins, an F1 race calendar, Shamsi dates** and similar features exist in the launcher.
  They are off by default and cost nothing; not worth a fork to remove.
- The launcher's `minSdk` is 26 (Android 8), so any Android/Google TV newer than 9 is in range.

## 5. What this eliminates from the original plan

| Original work item | Now |
|---|---|
| Write a launcher from scratch (Phase 4) | Eliminated. Configure via a theme folder in this repo |
| Write debloat tooling, restore script, drift check | Eliminated. Reuse `cleanyourtv/tools/` |
| Research TCL package purposes from nothing | Mostly eliminated. Start from the matching list's annotated header and verify each line on your set |
| ADB client that works around sandboxing | Eliminated. `tools/tv.py` needs only Python, no platform-tools |
| Build toolchain in this container | Replaced. The launcher needs the Android Gradle Plugin and AndroidX from `dl.google.com`, which this container's network policy denies (a public mirror was tried and is denied too). So the APK is built by a GitHub Actions workflow added to this repo, from the pinned source, with its SHA-256 recorded; you download the artifact and the install script pushes it. No SDK on your computer. (If you allow `dl.google.com` in the environment's network settings, it can also build here.) |
| Partner reviews | Kept, but targeted: Review 1b above covers the reused code; later reviews cover only our configuration, the matched list and real-TV results |

Still ours: the backup/manifest wrapper, the photo wallpaper theme, the approval workflow,
performance measurement, real-device testing and the plain-English documentation.

## 6. Wallpaper photographs: one decision needed

The engine is reused. The pictures are not: the bundled set is illustrated, you asked for
photography. Public-domain/CC0 photo sources (Wikimedia Commons, Pexels, Unsplash) are **denied
by this container's network policy**, so pick one:

- **A.** Allow `commons.wikimedia.org` and `upload.wikimedia.org` in the environment's network
  settings. I then fetch 12 to 16 CC0/public-domain landscape photographs, record each file's
  source URL and licence in the theme folder, and resize them to the TV's exact resolution.
- **B.** Drop your own photos (or ones you download yourself) into a folder in this repo; I
  optimise and wire them in.
- **C.** Use the bundled illustrated set for now and revisit later.

## 7. Next safe step

Unchanged from Phase 1, with two additions already made:

1. Run `tools/tv-discover.sh <TV-IP>` (macOS/Linux) or `tools\tv-discover.ps1 -Target <TV-IP>`
   (Windows) with the TV's home screen showing, following `docs/ADB-SETUP.md`. The script now
   also records the saved-Wi-Fi owner, the TV-input packages and TCL's install policy.
2. Commit the `discovery/` folder or paste `discovery/latest-summary.txt`, and tell me your
   computer's operating system and your answer to §6.

Then Phase 2 (backup + manifest, using the discovery output as the baseline) and Phase 3 (the
matched list reviewed line by line with you) follow, with no TV change before your approval.
