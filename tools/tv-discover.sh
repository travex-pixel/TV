#!/usr/bin/env bash
# tv-discover.sh — READ-ONLY discovery of a TCL Android/Google TV over ADB.
#
# It changes nothing on the TV. It only reads properties, package lists,
# settings, memory/storage figures and takes a screenshot of the current screen.
#
# Usage:  ./tools/tv-discover.sh <TV-IP>[:port]
# Output: discovery/<timestamp>/  (full logs)  and  discovery/latest-summary.txt
set -u

TARGET="${1:-}"
if [ -z "$TARGET" ]; then
  echo "Usage: $0 <TV-IP>[:port]   e.g. $0 192.168.1.42" >&2; exit 2
fi
case "$TARGET" in *:*) ;; *) TARGET="$TARGET:5555";; esac

ADB="${ADB:-adb}"
if ! command -v "$ADB" >/dev/null 2>&1; then
  echo "adb not found. Install Google's platform-tools (see docs/ADB-SETUP.md)," >&2
  echo "or run: ADB=/path/to/platform-tools/adb $0 $TARGET" >&2; exit 2
fi

STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="discovery/$STAMP"; mkdir -p "$OUT"
SUMMARY="$OUT/summary.txt"

log()  { echo "== $*" | tee -a "$SUMMARY"; }
run()  { # run <file> <adb shell command...>   (stdout+stderr to file)
  local f="$OUT/$1"; shift
  "$ADB" -s "$TARGET" shell "$@" >"$f" 2>&1
  echo "  saved $f ($(wc -l <"$f") lines)"
}

log "tv-discover $STAMP  target=$TARGET  adb=$("$ADB" version | head -1)"
"$ADB" connect "$TARGET" | tee "$OUT/adb-connect.txt"
STATE="$("$ADB" -s "$TARGET" get-state 2>&1 || true)"
log "adb state: $STATE"
if [ "$STATE" != "device" ]; then
  case "$STATE" in
    *unauthorized*) log "TV is connected but NOT authorised. Look at the TV screen for 'Allow USB debugging?', choose Always allow + OK, and re-run.";;
    *not\ found*|*offline*) log "TV not reachable at $TARGET. Check the IP in Settings > Network, that USB/Network debugging is ON, and that this computer is on the same Wi-Fi.";;
    *) log "Unexpected adb state: $STATE";;
  esac
  "$ADB" devices -l | tee -a "$SUMMARY"; exit 1
fi

# ---- identity ------------------------------------------------------------
run getprop.txt getprop
prop() { grep -m1 "^\[$1\]" "$OUT/getprop.txt" | sed 's/.*: \[\(.*\)\]$/\1/'; }
log "model=$(prop ro.product.model) brand=$(prop ro.product.brand) device=$(prop ro.product.device) board=$(prop ro.board.platform)/$(prop ro.hardware)"
log "android=$(prop ro.build.version.release) sdk=$(prop ro.build.version.sdk) security_patch=$(prop ro.build.version.security_patch)"
log "fingerprint=$(prop ro.build.fingerprint)"
log "build_id=$(prop ro.build.display.id) abi=$(prop ro.product.cpu.abilist) characteristics=$(prop ro.build.characteristics)"
log "tcl props: $(grep -ciE 'tcl|tvos|t-?vision' "$OUT/getprop.txt") lines mention TCL (see getprop.txt)"

# ---- hardware ------------------------------------------------------------
run cpuinfo.txt cat /proc/cpuinfo
run meminfo.txt cat /proc/meminfo
run df.txt df -h
run wm.txt 'wm size; wm density'
log "cpu cores=$(grep -c '^processor' "$OUT/cpuinfo.txt")  $(grep -m1 -iE 'hardware|model name' "$OUT/cpuinfo.txt")"
log "mem: $(grep -E 'MemTotal|MemAvailable' "$OUT/meminfo.txt" | tr -s ' ' | tr '\n' ' ')"
log "storage: $(grep -E ' /data$' "$OUT/df.txt" | tr -s ' ')"
log "display: $(tr '\n' ' ' <"$OUT/wm.txt")"

# ---- packages (full inventory, never modified) -----------------------------
run packages-all.txt pm list packages -f
run packages-system.txt pm list packages -s
run packages-user.txt pm list packages -3
run packages-disabled.txt pm list packages -d
run packages-enabled.txt pm list packages -e
run packages-uninstalled-for-user.txt pm list packages -u
run features.txt pm list features
log "packages: total=$(wc -l <"$OUT/packages-all.txt") system=$(wc -l <"$OUT/packages-system.txt") user=$(wc -l <"$OUT/packages-user.txt") disabled=$(wc -l <"$OUT/packages-disabled.txt")"
log "vendor-ish packages (tcl/tv/vision/ads):"
grep -iE 'tcl|\.tv\.|vision|ads|promo|recommend|analytic|report|stat' "$OUT/packages-all.txt" | sed 's/.*=//' | sort | tee -a "$SUMMARY"
log "leanback features: $(grep -cE 'leanback|live_tv|hdmi' "$OUT/features.txt") (see features.txt)"

# ---- launcher / home -------------------------------------------------------
run home-resolve.txt cmd package resolve-activity --brief -a android.intent.action.MAIN -c android.intent.category.HOME
run home-candidates.txt cmd package query-activities --brief -a android.intent.action.MAIN -c android.intent.category.HOME
run home-preferred.txt dumpsys package preferred-activities
run window-focus.txt 'dumpsys window windows | grep -E "mCurrentFocus|mFocusedApp"'
run activities-top.txt 'dumpsys activity activities | grep -E "topResumedActivity|mResumedActivity|ResumedActivity|mFocusedApp" '
run role-home.txt 'cmd role get-role-holders android.app.role.HOME'
log "current HOME resolves to: $(tail -1 "$OUT/home-resolve.txt")"
log "HOME candidates:"; grep -vE '^\s*$' "$OUT/home-candidates.txt" | tee -a "$SUMMARY"
log "HOME role holder: $(tr '\n' ' ' <"$OUT/role-home.txt")"
log "focused window: $(tr '\n' ' ' <"$OUT/window-focus.txt")"

# ---- settings (read-only baseline) ----------------------------------------
run settings-global.txt settings list global
run settings-system.txt settings list system
run settings-secure.txt settings list secure
log "animation scales: $(grep -E 'animator_duration_scale|transition_animation_scale|window_animation_scale' "$OUT/settings-global.txt" | tr '\n' ' ')"
log "secure settings readable: $(wc -l <"$OUT/settings-secure.txt") lines"

# ---- processes & performance baseline --------------------------------------
run ps.txt ps -A
run meminfo-summary.txt 'dumpsys meminfo | head -80'
run gfxinfo-launcher.txt 'dumpsys gfxinfo $(cmd package resolve-activity --brief -a android.intent.action.MAIN -c android.intent.category.HOME | tail -1 | cut -d/ -f1) | head -40'
run uptime.txt 'uptime; cat /proc/loadavg'
run appops-tcl.txt 'dumpsys package | grep -iE "^  Package \[(com\.tcl|com\.tv)" '
log "process count: $(($(wc -l <"$OUT/ps.txt")-1))  load: $(cat "$OUT/uptime.txt" | tail -1)"
log "top RSS (dumpsys meminfo):"; grep -A12 'Total PSS by process' "$OUT/meminfo-summary.txt" | head -14 | tee -a "$SUMMARY"

# ---- screenshot of whatever is on screen now ---------------------------------
if "$ADB" -s "$TARGET" exec-out screencap -p >"$OUT/screen-now.png" 2>"$OUT/screencap.err" && [ -s "$OUT/screen-now.png" ]; then
  log "screenshot saved: $OUT/screen-now.png ($(wc -c <"$OUT/screen-now.png") bytes)"
else
  log "screenshot FAILED (see screencap.err). Some firmware blocks screencap for protected content; try again with the home screen showing."
fi

# ---- adb self-info ------------------------------------------------------------
"$ADB" devices -l >"$OUT/adb-devices.txt" 2>&1
"$ADB" -s "$TARGET" shell id >"$OUT/adb-shell-id.txt" 2>&1
log "adb shell identity: $(cat "$OUT/adb-shell-id.txt")"

cp "$SUMMARY" discovery/latest-summary.txt
echo
echo "DONE. Full output in $OUT/. Paste the contents of discovery/latest-summary.txt into the chat,"
echo "or commit the whole discovery/ folder to the repository."
