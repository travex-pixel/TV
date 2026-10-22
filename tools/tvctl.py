#!/usr/bin/env python3
"""tvctl.py: backup, apply, restore and verify for one TV, driven by a manifest. Uses the adb binary.

    tvctl.py backup                          full read-only baseline into backup/<timestamp>/ + manifest
    tvctl.py apply <list> [--dry-run]        disable the packages in <list>, recording each original state first
    tvctl.py setting <ns> <key> <value|delete> [--dry-run]   change one setting, recording the original
    tvctl.py home <pkg/activity> [--dry-run] set the HOME activity, recording the original
    tvctl.py restore [--dry-run] [--pkg P]   undo every recorded change (packages, settings, home)
    tvctl.py verify                          compare the TV with the recorded changes (drift check)
    tvctl.py shot <name>                     screenshot the TV into shots/<name>.png
    tvctl.py bench <name>                    start-up timings, CPU and memory snapshot into bench/<name>/

Environment: TV_HOST (ip or ip:port, default port 5555), ADB (default: adb on PATH).
Rules: never uninstalls, never factory-resets, refuses to touch the protected packages unless
--allow <pkg> is given, refuses a TV whose fingerprint or serial differs from the manifest.
"""
import json, os, re, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKUP = ROOT / "backup"
CHANGES = BACKUP / "changes.json"
MANIFEST = BACKUP / "manifest.json"
PKG_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)+")
COMP_RE = re.compile(r"[A-Za-z_][\w.]*/[\w.$]+")
SETTING_RE = re.compile(r"[A-Za-z0-9_.:-]+")

# Load-bearing on TCL BeyondTV / RTD2851 Android TV 9 (from the sibling reports in cleanyourtv/examples)
# and Android basics. `apply` refuses these unless --allow <pkg> names them explicitly.
PROTECTED = {
    "android", "com.android.systemui", "com.android.settings", "com.android.tv.settings",
    "com.android.providers.settings", "com.android.providers.media", "com.android.providers.tv",
    "com.android.providers.downloads", "com.android.bluetooth", "com.android.inputdevices",
    "com.android.shell", "com.android.vending", "com.google.android.gms", "com.google.android.gsf",
    "com.google.android.packageinstaller", "com.google.android.webview", "com.google.android.tvlauncher",
    "com.google.android.tungsten.setupwraith", "com.google.android.inputmethod.latin",
    "com.google.android.apps.mediashell", "com.google.android.tv.remote.service",
    "com.tcl.tv", "com.tcl.tvinput", "com.tcl.tvpassthrough", "com.tcl.sourcemananger",
    "com.tcl.keycustomfunctionservice", "com.tcl.framework.custom", "com.tcl.tcl_bt_rcu_service",
    "com.tcl.autopair", "com.tcl.inputmethod.international", "com.tcl.settings", "com.tcl.initsetup",
    "com.tcl.factory.view", "com.tcl.showmode", "com.tcl.xian.StartandroidService",
    "com.tcl.appstatecontroller", "com.tcl.versionUpdateApp", "com.tcl.rc.ota",
    "com.realtek.netflix.setting", "com.android.WifiCountryService", "com.gathin.tvhome",
}
IDENTITY_PROPS = ("ro.product.manufacturer", "ro.product.model", "ro.product.device",
                  "ro.build.fingerprint", "ro.build.version.release", "ro.build.version.sdk",
                  "ro.build.version.incremental", "ro.serialno", "ro.boot.serialno")
SETTING_KEYS = {"global": ("window_animation_scale", "transition_animation_scale",
                           "animator_duration_scale", "private_dns_mode", "private_dns_specifier"),
                "secure": ("screensaver_components", "screensaver_enabled",
                           "enabled_accessibility_services", "accessibility_enabled")}
HOME_QUERY = ("cmd package resolve-activity --brief -a android.intent.action.MAIN "
              "-c android.intent.category.HOME")


def target():
    host = os.environ.get("TV_HOST", "")
    if not host:
        sys.exit("set TV_HOST to the TV's address, e.g. TV_HOST=192.168.0.103 tools/tvctl.py backup")
    return host if ":" in host else host + ":5555"


def adb(*args, check=True, binary=False):
    cmd = [os.environ.get("ADB", "adb"), "-s", target(), *args]
    r = subprocess.run(cmd, capture_output=not binary, stdout=subprocess.PIPE if binary else None,
                       text=not binary, timeout=300)
    if check and r.returncode != 0:
        sys.exit(f"adb failed ({r.returncode}): {' '.join(args)}\n{'' if binary else r.stderr}")
    return r.stdout if binary else (r.stdout or "")


def shell(cmd):
    """One shell command, CRLF-normalised. Every argument interpolated here was regex-checked."""
    return adb("shell", cmd, check=False).replace("\r\n", "\n").strip()


def connect():
    subprocess.run([os.environ.get("ADB", "adb"), "connect", target()], capture_output=True, text=True)
    state = adb("get-state", check=False).strip()
    if state != "device":
        sys.exit(f"TV at {target()} is not available (adb state: {state or 'none'}). "
                 "Check the IP, USB debugging, and the Allow prompt on the TV.")


def identity():
    return {p: shell(f"getprop {p}") for p in IDENTITY_PROPS}


def check_identity(manifest):
    now = identity()
    want = manifest["device"]
    for key in ("ro.build.fingerprint", "ro.serialno"):
        if want.get(key) and now.get(key) != want.get(key):
            sys.exit(f"REFUSING: this TV's {key} is {now.get(key)!r}, the manifest was made for "
                     f"{want.get(key)!r}. Wrong TV, or firmware changed. Nothing was done.")
    return now


def packages(flag=""):
    out = shell(f"pm list packages {flag}".strip())
    return {l.split(":", 1)[1] for l in out.splitlines() if l.startswith("package:")}


def state_of(pkg, installed=None, disabled=None):
    installed = packages() if installed is None else installed
    disabled = packages("-d") if disabled is None else disabled
    return "absent" if pkg not in installed else "disabled" if pkg in disabled else "enabled"


def home_now():
    last = shell(HOME_QUERY).splitlines()[-1:] or [""]
    return last[0].strip() if COMP_RE.fullmatch(last[0].strip()) else ""


def load_json(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    os.replace(tmp, path)


def need_manifest():
    m = load_json(MANIFEST, None)
    if not m:
        sys.exit("no backup/manifest.json yet: run `tvctl.py backup` first")
    return m


def read_list(path):
    names = []
    for n, line in enumerate(Path(path).read_text(encoding="utf-8-sig").splitlines(), 1):
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        name = line.split()[0]
        if not PKG_RE.fullmatch(name):
            sys.exit(f"{path}:{n}: not a package name: {name!r}")
        names.append(name)
    return names


def log(entry):
    changes = load_json(CHANGES, {"version": 1, "log": [], "packages": {}, "settings": {}, "home": None})
    changes["log"].append(dict(entry, at=time.strftime("%Y-%m-%dT%H:%M:%S%z")))
    save_json(CHANGES, changes)
    return changes


# ---------------------------------------------------------------- commands
def cmd_backup(args):
    connect()
    ts = time.strftime("%Y%m%d-%H%M%S")
    out = BACKUP / ts
    out.mkdir(parents=True, exist_ok=True)
    dev = identity()
    dumps = {
        "getprop.txt": "getprop",
        "packages-all.txt": "pm list packages -f", "packages-enabled.txt": "pm list packages -e",
        "packages-disabled.txt": "pm list packages -d", "packages-system.txt": "pm list packages -s",
        "packages-user.txt": "pm list packages -3",
        "settings-global.txt": "settings list global", "settings-system.txt": "settings list system",
        "settings-secure.txt": "settings list secure",
        "home.txt": HOME_QUERY,
        "home-candidates.txt": "cmd package query-activities --brief -a android.intent.action.MAIN -c android.intent.category.HOME",
        "meminfo.txt": "dumpsys meminfo", "df.txt": "df -h", "top.txt": "top -b -n 1 -m 30",
        "accessibility.txt": "settings get secure enabled_accessibility_services",
        "tvinput.txt": "dumpsys tv_input", "appops-launcher.txt": "appops get com.google.android.tvlauncher",
    }
    for name, cmd in dumps.items():
        (out / name).write_text(shell(cmd) + "\n")
        print(f"  {name}")
    installed, disabled = packages(), packages("-d")
    settings = {ns: {k: shell(f"settings get {ns} {k}") for k in keys} for ns, keys in SETTING_KEYS.items()}
    manifest = {
        "version": 1, "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "host": target(),
        "device": dev, "home": home_now(), "settings": settings,
        "packages": {p: ("disabled" if p in disabled else "enabled") for p in sorted(installed)},
        "backup_dir": str(out.relative_to(ROOT)),
    }
    if MANIFEST.exists():
        old = load_json(MANIFEST, {})
        if old.get("device", {}).get("ro.build.fingerprint") != dev["ro.build.fingerprint"]:
            sys.exit("a manifest for a different TV/firmware exists; move backup/manifest.json aside first")
        print("manifest.json already exists and is kept (first baseline wins); this run is an extra snapshot")
        save_json(out / "manifest-snapshot.json", manifest)
    else:
        save_json(MANIFEST, manifest)
        print(f"manifest written: {MANIFEST.relative_to(ROOT)}")
    # APK paths of everything plus the APKs of the candidate list, if given (small; nothing is ever deleted).
    if args and args[0] == "--apks":
        (out / "apks").mkdir(exist_ok=True)
        for pkg in read_list(args[1]):
            path = shell(f"pm path {pkg}").replace("package:", "").splitlines()[:1]
            if path and path[0].startswith("/"):
                r = subprocess.run([os.environ.get("ADB", "adb"), "-s", target(), "pull", path[0],
                                    str(out / "apks" / f"{pkg}.apk")], capture_output=True, text=True)
                print(f"  apk {pkg}: {'ok' if r.returncode == 0 else 'not pullable'}")
    shot(out / "screen-home.png", go_home=True)
    print(f"backup complete: {out.relative_to(ROOT)}  ({len(installed)} packages, {len(disabled)} disabled, "
          f"home={manifest['home']})")


def shot(path, go_home=False):
    if go_home:
        shell("input keyevent KEYCODE_HOME"); time.sleep(3)
    remote = "/data/local/tmp/tvctl-shot.png"
    shell(f"screencap -p {remote}")
    subprocess.run([os.environ.get("ADB", "adb"), "-s", target(), "pull", remote, str(path)],
                   capture_output=True, text=True)
    shell(f"rm -f {remote}")
    size = path.stat().st_size if path.exists() else 0
    print(f"  screenshot {path} ({size} bytes){'  <- empty: protected content on screen?' if size == 0 else ''}")


def cmd_apply(args):
    dry = "--dry-run" in args
    allow = {args[i + 1] for i, a in enumerate(args) if a == "--allow" and i + 1 < len(args)}
    lists = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] != "--allow")]
    if not lists:
        sys.exit("usage: tvctl.py apply <list> [--dry-run] [--allow <pkg>]")
    names = read_list(lists[0])
    manifest = need_manifest()
    connect(); check_identity(manifest)
    blocked = [n for n in names if n in PROTECTED and n not in allow]
    if blocked:
        sys.exit("REFUSING: the list names protected packages: " + ", ".join(blocked) +
                 "\nRemove them from the list, or pass --allow <pkg> for each one deliberately.")
    changes = load_json(CHANGES, {"version": 1, "log": [], "packages": {}, "settings": {}, "home": None})
    installed, disabled = packages(), packages("-d")
    print(f"{'DRY RUN: ' if dry else ''}{len(names)} packages in {lists[0]}")
    done = 0
    for pkg in names:
        before = state_of(pkg, installed, disabled)
        if before != "enabled":
            print(f"  skip   {pkg}: {before}")
            continue
        if pkg not in changes["packages"]:
            changes["packages"][pkg] = {"original": before, "list": str(lists[0])}
            if not dry:
                save_json(CHANGES, changes)      # original state on disk BEFORE the command runs
        if dry:
            print(f"  would  pm disable-user --user 0 {pkg}")
            continue
        out = shell(f"pm disable-user --user 0 {pkg}")
        after = state_of(pkg, installed, packages("-d"))
        log({"action": "disable", "package": pkg, "before": before, "after": after, "output": out})
        print(f"  {'ok    ' if after == 'disabled' else 'FAILED'} {pkg}: {out or after}")
        done += after == "disabled"
    if not dry:
        print(f"disabled {done}; now disabled on TV: {len(packages('-d'))}. Undo: tvctl.py restore")


def cmd_setting(args):
    dry = "--dry-run" in args
    args = [a for a in args if a != "--dry-run"]
    if len(args) != 3 or args[0] not in ("global", "system", "secure") or not SETTING_RE.fullmatch(args[1]) \
            or not SETTING_RE.fullmatch(args[2]):
        sys.exit("usage: tvctl.py setting <global|system|secure> <key> <value|delete> [--dry-run]")
    ns, key, value = args
    manifest = need_manifest(); connect(); check_identity(manifest)
    changes = load_json(CHANGES, {"version": 1, "log": [], "packages": {}, "settings": {}, "home": None})
    original = shell(f"settings get {ns} {key}")
    changes["settings"].setdefault(f"{ns}:{key}", {"original": original})
    print(f"{'DRY RUN: ' if dry else ''}{ns} {key}: {original!r} -> {value!r}")
    if dry:
        return
    save_json(CHANGES, changes)
    out = shell(f"settings delete {ns} {key}" if value == "delete" else f"settings put {ns} {key} {value}")
    now = shell(f"settings get {ns} {key}")
    log({"action": "setting", "key": f"{ns}:{key}", "before": original, "after": now, "output": out})
    print(f"  now {now!r}")


def cmd_home(args):
    dry = "--dry-run" in args
    comp = [a for a in args if a != "--dry-run"]
    if len(comp) != 1 or not COMP_RE.fullmatch(comp[0]):
        sys.exit("usage: tvctl.py home <package/activity> [--dry-run]")
    manifest = need_manifest(); connect(); check_identity(manifest)
    changes = load_json(CHANGES, {"version": 1, "log": [], "packages": {}, "settings": {}, "home": None})
    original = home_now()
    if changes.get("home") is None:
        changes["home"] = {"original": original}
    print(f"{'DRY RUN: ' if dry else ''}HOME {original} -> {comp[0]}")
    if dry:
        return
    save_json(CHANGES, changes)
    out = shell(f"cmd package set-home-activity --user 0 {comp[0]}")
    now = home_now()
    log({"action": "home", "before": original, "after": now, "output": out})
    print(f"  HOME now resolves to {now}  {'OK' if now.split('/')[0] == comp[0].split('/')[0] else 'NOT SWITCHED'}")


def cmd_restore(args):
    dry = "--dry-run" in args
    only = [args[i + 1] for i, a in enumerate(args) if a == "--pkg" and i + 1 < len(args)]
    manifest = need_manifest()
    changes = load_json(CHANGES, None)
    if not changes:
        print("no backup/changes.json: nothing was changed through tvctl, nothing to restore"); return
    connect(); check_identity(manifest)
    print(f"{'DRY RUN: ' if dry else ''}restoring from {CHANGES.relative_to(ROOT)}")
    # 1. Home first, so the TV always has a usable home before anything else moves.
    home = changes.get("home")
    if home and home.get("original") and not only:
        orig = home["original"]
        if orig.split("/")[0] in packages("-d") and orig.split("/")[0] not in changes["packages"]:
            print(f"  WARNING: original home {orig} is disabled and not in the record; enabling it anyway")
        if not dry:
            shell(f"pm enable {orig.split('/')[0]}")
            out = shell(f"cmd package set-home-activity --user 0 {orig}")
            log({"action": "restore-home", "to": orig, "output": out, "after": home_now()})
        print(f"  home   -> {orig}{'' if dry else '  now: ' + home_now()}")
    # 2. Packages.
    installed, disabled = packages(), packages("-d")
    for pkg, rec in sorted(changes["packages"].items()):
        if only and pkg not in only:
            continue
        cur = state_of(pkg, installed, disabled)
        if rec["original"] != "enabled":
            print(f"  leave  {pkg}: was {rec['original']} before, now {cur}"); continue
        if cur == "enabled":
            print(f"  ok     {pkg}: already enabled"); continue
        if cur == "absent":
            print(f"  ??     {pkg}: not installed any more (never uninstalled by tvctl)"); continue
        if dry:
            print(f"  would  pm enable {pkg}"); continue
        out = shell(f"pm enable {pkg}")
        after = state_of(pkg, installed, packages("-d"))
        log({"action": "restore-enable", "package": pkg, "after": after, "output": out})
        print(f"  {'ok    ' if after == 'enabled' else 'FAILED'} {pkg}: {out or after}")
    # 3. Settings.
    if not only:
        for key, rec in sorted(changes.get("settings", {}).items()):
            ns, name = key.split(":", 1)
            orig = rec["original"]
            cmd = f"settings delete {ns} {name}" if orig in ("null", "") else f"settings put {ns} {name} {orig}"
            if dry:
                print(f"  would  {cmd}"); continue
            out = shell(cmd)
            log({"action": "restore-setting", "key": key, "to": orig, "output": out,
                 "after": shell(f"settings get {ns} {name}")})
            print(f"  ok     {key} -> {orig!r}")
    if not dry:
        print(f"restore finished. Disabled now: {len(packages('-d'))} (baseline had "
              f"{sum(1 for s in manifest['packages'].values() if s == 'disabled')}). Verify: tvctl.py verify")


def cmd_verify(_):
    manifest = need_manifest(); connect(); check_identity(manifest)
    changes = load_json(CHANGES, {"packages": {}, "settings": {}, "home": None})
    installed, disabled = packages(), packages("-d")
    drift = 0
    for pkg, rec in sorted(changes["packages"].items()):
        cur = state_of(pkg, installed, disabled)
        flag = "" if cur == "disabled" else "  <- DRIFT (re-enabled, e.g. by TCL at boot or an update)"
        drift += bool(flag); print(f"  {pkg}: {cur}{flag}")
    base_disabled = {p for p, s in manifest["packages"].items() if s == "disabled"}
    extra = disabled - base_disabled - set(changes["packages"])
    missing = base_disabled - disabled
    for p in sorted(extra): print(f"  {p}: disabled but not by tvctl  <- note")
    for p in sorted(missing): print(f"  {p}: was disabled at baseline, now enabled  <- note")
    print(f"home: {home_now()}   (baseline {manifest['home']})")
    print(f"{drift} drifted of {len(changes['packages'])} recorded")
    return 1 if drift else 0


def cmd_shot(args):
    connect(); d = ROOT / "shots"; d.mkdir(exist_ok=True)
    shot(d / f"{re.sub(r'[^A-Za-z0-9_.-]', '_', args[0] if args else 'shot')}.png")


def cmd_bench(args):
    connect(); name = re.sub(r"[^A-Za-z0-9_.-]", "_", args[0] if args else time.strftime("%Y%m%d-%H%M%S"))
    d = ROOT / "bench" / name; d.mkdir(parents=True, exist_ok=True)
    res = {"created": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "home": home_now(), "launch_ms": {}}
    (d / "top.txt").write_text(shell("top -b -n 1 -m 25") + "\n")
    (d / "meminfo.txt").write_text(shell("dumpsys meminfo") + "\n")
    mem = shell("cat /proc/meminfo")
    res["mem_available_kb"] = int(re.search(r"MemAvailable:\s+(\d+)", mem).group(1)) if "MemAvailable" in mem else None
    res["processes"] = len(shell("ps -A").splitlines()) - 1
    targets = {"home": None, "netflix": "com.netflix.ninja", "youtube": "com.google.android.youtube.tv"}
    for label, pkg in targets.items():
        times = []
        for _ in range(3):
            if pkg:
                shell(f"am force-stop {pkg}")
            time.sleep(2)
            cmd = ("am start -W -a android.intent.action.MAIN -c android.intent.category.HOME" if not pkg
                   else f"am start -W $(cmd package resolve-activity --brief -a android.intent.action.MAIN "
                        f"-c android.intent.category.LEANBACK_LAUNCHER {pkg} | tail -n 1)")
            out = shell(cmd)
            m = re.search(r"TotalTime:\s+(\d+)", out)
            times.append(int(m.group(1)) if m else None)
            time.sleep(4)
            shell("input keyevent KEYCODE_HOME"); time.sleep(2)
        res["launch_ms"][label] = times
        print(f"  {label}: {times} ms (cold start x3, TotalTime)")
    save_json(d / "bench.json", res)
    print(f"bench saved: {d.relative_to(ROOT)}  MemAvailable={res['mem_available_kb']} kB processes={res['processes']}")


COMMANDS = {"backup": cmd_backup, "apply": cmd_apply, "setting": cmd_setting, "home": cmd_home,
            "restore": cmd_restore, "verify": cmd_verify, "shot": cmd_shot, "bench": cmd_bench}
if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        sys.exit(__doc__)
    sys.exit(COMMANDS[sys.argv[1]](sys.argv[2:]) or 0)
