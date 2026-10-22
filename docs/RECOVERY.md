# Recovery: how to undo everything, in the fewest steps

## If the TV shows a strange home screen or the new launcher will not open

With the remote only, no phone needed:

1. Press the **Settings** button on the remote (or open Settings from whatever screen shows).
2. **Apps → See all apps → Show system apps** (if asked) → find **Android TV Home** (or
   "Home" by Google) → **Enable**.
3. Press the Home button. The old home screen is back. Everything else keeps working.

## Full undo from the phone (Termux, in the TV folder)

```
export TV_HOST=192.168.0.103
python3 tools/tvctl.py restore --dry-run      # shows what will happen, changes nothing
python3 tools/tvctl.py restore                # puts Home, packages and settings back
python3 tools/tvctl.py launcher uninstall     # optional: removes the new launcher
```

This re-enables the original launcher and the 13 disabled packages, sets Home back, restores the
animation scales and removes the Private DNS setting. It never resets or deletes anything.

## Only put DNS back (if some app cannot connect)

```
python3 tools/tvctl.py setting global private_dns_mode opportunistic
```

## Reconnecting ADB later

The TV remembers the phone. After a TV restart: `adb connect 192.168.0.103`. If the TV stops
answering, on the TV: Settings → System → Developer options → USB debugging off, then on again.
If Developer options has vanished, press OK 7 times on the build number under About.

## Closing ADB when finished

Developer options → **USB debugging off** and **Revoke USB debugging authorisations**, then
restart the TV. The launcher and all changes keep working without debugging.
