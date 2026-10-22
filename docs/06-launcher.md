# Phase 4 and 5 — The launcher: configuration, reviews, install plan

Date: 2026-10-23. Launcher: CleanYourTV `com.gathin.tvhome` 2.5, built unmodified from the
vendored source by this repository's GitHub Actions workflow and committed to `launcher-apk/`
with its SHA-256. `tvctl.py launcher install` refuses an APK whose checksum differs.

## Configuration (no source change; a theme pushed to the TV)

`profile/theme/config.json`:

| Key | Value | Why |
|---|---|---|
| `dock_apps` | Netflix, YouTube, Disney+, Prime Video, Crunchyroll | your order; all five are installed and enabled |
| `columns` | 5 | the dock has exactly `columns` slots; 5 favourites need 5 |
| `fill_dock` | false | no surprise apps padding the dock |
| `hidden_apps` / `live_tv_package` | `com.tcl.tv` | Live TV and HDMI live in the Inputs menu, as on the AP08 field report; the package stays enabled |
| `app_library` | true | every other installed app reachable from one "App library" row; add/remove Home tiles with the remote |
| `show_network_pill` | false | removes the Wi-Fi name pill, so no location permission is granted to the launcher at all |
| `wallpaper`, `wallpaper_rotation_minutes` 30, `wallpaper_order` shuffle, `wallpaper_dim` 25 | the bundled 14 landscapes (your option C), rotating while Home is visible, dimmed a quarter so white text stays legible | RGB_565 decode, ~4 MB per image, next image decoded off the main thread |
| `ambient_glow` | false | the coloured glow behind the dock fights a photographic background; off for a calmer Apple-TV look |
| `home_idle_clock_minutes` | 0 | the TV's own screensaver settings stay in charge |

Everything not listed keeps the launcher's defaults (dark background, glass focus highlight,
greeting + large clock + date, Inputs and Settings pills, deterministic D-pad rules).

## Partner Review 3 — Product designer (targeted at this configuration)

- Immediately understandable: one row of five favourites at the bottom, name of the focused
  one in large type, clock top-left, two pills top-right. Nothing else on the first screen.
- Reach: favourites are one press away from Home. Everything else is one row down.
- Legibility at distance: Outfit at the launcher's sizes was designed for 1080p TVs; the 25 %
  dim keeps the wallpaper from washing out names. To be confirmed on the real screenshot.
- Premium feel: photographic wallpapers would be better than the illustrated set; that was
  your call for now and is a theme-folder swap later, no reinstall.
- Focus states: a single sprung glass highlight plus scale; obvious. Reduced-motion stays off
  because this GPU family handled the normal motion on the sibling C715; revisit if it stutters.
- Complexity cut: network pill off, ambient glow off, no festival skin, no race calendar, no
  clock screensaver takeover. Nothing left that needs explaining.

## Partner Review 4 — Architecture and performance (targeted)

Already covered for the code in `docs/02-cleanyourtv-review.md` (no INTERNET permission, no
services unless opted in, ~430 KB, RGB_565 bitmaps, RecyclerView only). Specific to this TV:

- 32-bit ARMv7: the APK is pure Dalvik bytecode, no native libraries, so there is no ABI issue.
- minSdk 26 vs TV SDK 28: fine. targetSdk 34 on an Android 9 host: Android applies the host's
  behaviour, not the target's; the field report on this exact build ran version 2.5 / code 6.
- Memory: 14 wallpapers are decoded one at a time (one bitmap resident, next decoded in a
  background executor), not preloaded. With 450 MB available this is comfortable.
- Startup: the first wallpaper is decoded on the main thread by design so Home's first frame
  already has it; at 1080p RGB_565 that is tens of milliseconds. Measured by `bench after`.
- Background: nothing runs when Home is not visible (`WallpaperPlayer.stop()` on pause). No
  accessibility service is enabled in this plan: on this firmware the Input and Settings
  buttons go through TCL's own path and worked on the AP08 unit without one.
- Risk accepted: the launcher is listed in the stock home's app row too, so it can be opened
  from there for testing without any Home change.

## Phase 5 install plan (stock launcher untouched)

1. `tvctl.py launcher install` — `adb install -r`, checksum-verified. Home still resolves to the
   stock launcher.
2. `tvctl.py launcher theme` — pushes `config.json` and the wallpapers to the launcher's own
   files directory and force-stops it so it reads them.
3. `tvctl.py launcher start` — starts it explicitly, waits, screenshots, checks the crash buffer.
4. You test with the remote: D-pad in all directions, OK on each dock app, Back from the app
   (the Back key from an app returns to whatever launched it: the new launcher), Home key
   (returns to the **stock** launcher at this stage, by design), Inputs pill, Settings pill,
   App library, wait 30 min or reopen for wallpaper rotation.
5. Only after that passes do I ask for approval to switch Home (`tvctl.py home`), which is
   recorded and undone by `tvctl.py restore`; the stock launcher stays enabled even then.

Partner Review 5 (security/adversarial QA) runs after step 4 against the real screenshots and
the TV's state, in `docs/07-test-results.md`.
