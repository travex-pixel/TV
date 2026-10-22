# Phase 2 and 3 — Backup design, restore tooling, and the debloat proposal

Date: 2026-10-23. Status: **tooling written and tested against a simulated TV; nothing applied
to the real TV yet. Waiting for your approval on the questions at the end.**

## 1. Baseline evidence already in the repository

`discovery/20261023-000534/` holds the first read-only run: full package inventory with APK
paths (156 packages, 20 already disabled), all three settings namespaces, system properties,
process list, memory summary, HOME resolution and a screenshot. Two observations from it:

- **Load average 19.6 on a 4-core CPU after 16 days of uptime.** That is a very busy TV. The
  process list shows `voice_ap`, two `katniss` voice processes, `sitatvservice`, and resident
  TCL services (`bi`, `tclhome_passive`, `partnercustomizer`, `messagebox`, `smartalexa`,
  `MultiScreenInteraction_TV`). The bench command below records per-process CPU so the
  before/after comparison is real, not guessed.
- Only 430 MB of 2 GB RAM was available. Netflix and the stock launcher held 136 MB each.
- The screenshot shows the stock home's Apps tab under the Developer options panel. A clean
  home-tab screenshot (with its promo rows) is taken by the backup command.

## 2. Backup, change manifest and restore: `tools/tvctl.py`

One small tool (adb only, no Python packages, runs in Termux) replaces CleanYourTV's
`disable.sh`/`restore.sh`/`recovery.py` for the TV operations, because those need the
`adb-shell` Python package with a native crypto dependency that may not build on the phone.
CleanYourTV's lists, field reports, launcher and theme format are still what we reuse.

| Command | What it does |
|---|---|
| `backup` | Read-only. Writes `backup/<timestamp>/` (getprop, package lists, settings, HOME, memory, `top`, TV-input dump, home screenshot) and `backup/manifest.json`: device identity (fingerprint, serial), the enabled/disabled state of **every** package, HOME, and the settings we might touch. The first manifest is never overwritten. `--apks <list>` also pulls the APKs of listed packages. |
| `apply <list> [--dry-run] [--allow pkg]` | Disables listed packages one `pm disable-user --user 0` at a time. Before each command the package's original state is written to `backup/changes.json`. Skips packages already disabled or absent. **Refuses** a list naming any of 40 protected packages (Live TV, inputs, remote, keyboards, Play, Chromecast, the stock launcher, updater) unless `--allow` names them. Verifies each result from `pm list packages -d`, not from the exit code. |
| `setting <ns> <key> <value>` / `home <component>` | Same pattern for settings and the HOME switch: original recorded first, then changed, then read back. |
| `restore [--dry-run] [--pkg P]` | Replays `changes.json` in a safe order: HOME back to the original first, then re-enables only packages that were **enabled** before we touched them, then settings. Prints every action and result. |
| `verify` | Drift check: which recorded packages TCL or an update re-enabled, and anything disabled outside the tool. |
| `shot <name>` / `bench <name>` | Real TV screenshot; cold-start timings (3 runs each for Home, Netflix, YouTube), `top`, memory, process count into `bench/<name>/`. |

Every command first compares the TV's fingerprint **and serial number** with the manifest and
refuses on a mismatch. Nothing in the tool can uninstall, clear data or reset.

**What cannot be backed up** (unchanged from Phase 1): app private data, account state,
protected vendor partitions. Not needed for this project because nothing is deleted.

### Partner Review 2 — Disaster recovery (results)

The tool was exercised end to end against a simulated TV that answers like this firmware,
including a package the firmware refuses to disable and TCL's boot-time re-enabling:

| Scenario | Result |
|---|---|
| `apply` before any backup exists | refused |
| List containing a protected package (`com.tcl.tv`) | refused, names the package |
| `--dry-run` | prints the commands, writes nothing to the TV or to `changes.json` |
| Real apply with one already-disabled and one refused package | 4 disabled, 1 skipped, 1 reported FAILED with the firmware's message; nothing else aborted |
| `verify` after TCL re-enables a package at boot | reports the drift, exit code 1 |
| Setting change + HOME switch to the new launcher | originals recorded, read-back confirmed |
| `restore --dry-run` then `restore` | HOME back to the stock launcher first, every package back to its original state, the already-disabled factory package left alone, setting restored; final disabled count equals the baseline |
| Different serial number | refused before any command |

Not simulated, and stated as such: an ADB disconnect mid-run (the tool records state before
each command, so a re-run resumes safely), a launcher that crash-loops (the stock launcher is
never disabled in Phase 5's first install, so the Home button keeps working), and the TV
rebooting mid-apply (each `pm` call is atomic on the TV side). The one scenario with no
software recovery is losing ADB access entirely, which is why `docs/ADB-SETUP.md` covers
re-enabling it from the TV's own Settings, and why the TV's own Settings → Apps page can
re-enable any package by hand.

## 3. Debloat proposal (Phase 3)

Full list with per-line comments: `profile/debloat-proposed.txt`. Evidence for every line
comes from the sibling lists on the same board (`cleanyourtv/examples/tcl-beyondtv-rt2851`,
`tcl-55c715`, `tcl-beyondtv-pl`, `tcl-beyondtv2-latin-america`) and the AP08 field report;
"process resident" means it was running in your discovery process list.

**Tier 1, recommended (13 packages).** Telemetry, promo feeds and recommendation rows:
`com.tcl.bi`, `com.tcl.tv.tclhome_passive`, `com.tcl.partnercustomizer`, `com.tcl.messagebox`,
`com.tcl.esticker`, `com.tcl.waterfall.overseas`, Google's two recommendation services,
feedback and bug-report uploaders, partner setup, one-time initializer, TCL auto-install
config. Effect: fewer resident processes, no TCL promo rows, no "send feedback" uploads. On
the stock home, `partnercustomizer` also supplies the Inputs icon; the remote's Source button
still works and the new launcher has its own Inputs menu. Confidence high: identical lines are
in daily use on a C715 with the same board. `esticker` may re-enable itself; harmless.
What it does **not** change: ads inside apps, and the stock home's own Google rows until the
launcher is replaced.

**Tier 2, optional.** Grouped so you can answer per group:
- 2a Google voice stack (6 packages): the biggest performance lever on this firmware
  (voice processes burn CPU continuously; ~100-200 MB freed on siblings). Cost: the mic button
  and voice search stop working. Alexa is listed separately.
- 2b Miracast and TCL's phone-link app (MagiConnect/T-Cast). Chromecast stays either way.
- 2c TCL extras: TV Guard cleaner and TCL app store (only after the launcher is installed),
  user center and note reminder (TCL re-enables both at boot, so they barely stick), key help,
  agreement screens, duplicate WebView, USB media centre, copy-to-TV.
- 2d Apps you may not use: Play Movies, YouTube Music, Play Games, TalkBack, calendar/contacts
  sync, print spooler, Ambient screensaver, PVR player, Samba, TCL video call, TCL browser.

**Tier 3, not recommended.** Everything load-bearing; the tool refuses them. Includes the
firmware updater (kept) and the stock launcher (kept until Phase 5 proves the replacement and
you approve the switch).

**Settings changes proposed (all recorded and reversible):**
- Animation scales 1.0 → 0.5 on all three (window, transition, animator). Visible snappiness
  on a slow GPU, zero functional risk. Undo: `tvctl.py restore` or Developer options.
- Private DNS to an ad-blocking resolver: **optional, off by default.** Blocks ad and tracker
  domains in every app but not YouTube ads, and that resolver then sees all DNS lookups.

**Order of operations:** backup → Tier 1 (one batch of 13, screenshot and check after) →
approved Tier 2 groups (one group per batch, check after each) → reboot → `verify` →
Phase 4/5 launcher.

## 4. Questions for you (answer by number)

1. **Tier 1**: approve all 13, or name any to leave out?
2. **Tier 2**: which groups, if any: 2a voice, 2b mirroring, 2c TCL extras, 2d unused apps
   (name the apps you actually use from 2d).
3. **Animation scales to 0.5**: yes or no?
4. **Private DNS ad-blocking**: yes or no?
5. **Dock favourites, in order** (4 to 6). Installed on your TV: YouTube, Netflix, Prime Video,
   Disney+, Stan, Foxtel, Kayo, 9Now, 7plus, 10play, Paramount+, Crunchyroll, Twitch, Spotify,
   ESPN, NBA, AirScreen, Play Store, Play Movies, YouTube Music.
6. **Wallpaper photos**: A allow Wikimedia Commons in the environment, B your own photos, or
   C bundled illustrations for now.
