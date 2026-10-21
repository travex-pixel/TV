# tv-discover.ps1 - READ-ONLY discovery of a TCL Android/Google TV over ADB (Windows).
#
# It changes nothing on the TV. It only reads properties, package lists,
# settings, memory/storage figures and takes a screenshot of the current screen.
#
# Usage (PowerShell, from the repository folder):
#   .\tools\tv-discover.ps1 -Target 192.168.1.42
#   .\tools\tv-discover.ps1 -Target 192.168.1.42 -Adb "C:\platform-tools\adb.exe"
# Output: discovery\<timestamp>\  and  discovery\latest-summary.txt
param(
  [Parameter(Mandatory=$true)][string]$Target,
  [string]$Adb = "adb"
)
$ErrorActionPreference = "Continue"
if ($Target -notmatch ":") { $Target = "$Target`:5555" }
if (-not (Get-Command $Adb -ErrorAction SilentlyContinue)) {
  Write-Host "adb not found. Download platform-tools (see docs\ADB-SETUP.md) and pass -Adb C:\path\platform-tools\adb.exe"; exit 2
}
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$Out = Join-Path "discovery" $Stamp
New-Item -ItemType Directory -Force -Path $Out | Out-Null
$Summary = Join-Path $Out "summary.txt"
function Log($m) { "== $m" | Tee-Object -FilePath $Summary -Append }
function Run($file, $cmd) {
  $f = Join-Path $Out $file
  & $Adb -s $Target shell $cmd 2>&1 | Out-File -Encoding utf8 $f
  Write-Host "  saved $f"
}
function Prop($name) {
  $line = Select-String -Path (Join-Path $Out "getprop.txt") -Pattern ("^\[" + [regex]::Escape($name) + "\]") | Select-Object -First 1
  if ($line) { return ($line.Line -replace '.*: \[(.*)\]$', '$1') } else { return "" }
}

Log "tv-discover $Stamp target=$Target adb=$((& $Adb version)[0])"
& $Adb connect $Target | Tee-Object -FilePath (Join-Path $Out "adb-connect.txt")
$State = (& $Adb -s $Target get-state 2>&1) -join " "
Log "adb state: $State"
if ($State -ne "device") {
  if ($State -match "unauthorized") { Log "TV is connected but NOT authorised. On the TV choose 'Always allow' + OK on the 'Allow USB debugging?' prompt, then re-run." }
  else { Log "TV not reachable at $Target. Check the IP (Settings > Network), that USB/Network debugging is ON, and that this PC is on the same Wi-Fi." }
  & $Adb devices -l | Tee-Object -FilePath $Summary -Append; exit 1
}

# identity
Run "getprop.txt" "getprop"
Log "model=$(Prop ro.product.model) brand=$(Prop ro.product.brand) device=$(Prop ro.product.device) board=$(Prop ro.board.platform)/$(Prop ro.hardware)"
Log "android=$(Prop ro.build.version.release) sdk=$(Prop ro.build.version.sdk) security_patch=$(Prop ro.build.version.security_patch)"
Log "fingerprint=$(Prop ro.build.fingerprint)"
Log "build_id=$(Prop ro.build.display.id) abi=$(Prop ro.product.cpu.abilist) characteristics=$(Prop ro.build.characteristics)"

# hardware
Run "cpuinfo.txt" "cat /proc/cpuinfo"
Run "meminfo.txt" "cat /proc/meminfo"
Run "df.txt" "df -h"
Run "wm.txt" "wm size; wm density"
Log ("cpu cores=" + (Select-String -Path (Join-Path $Out "cpuinfo.txt") -Pattern "^processor").Count)
Log ("mem: " + ((Select-String -Path (Join-Path $Out "meminfo.txt") -Pattern "MemTotal|MemAvailable" | ForEach-Object { $_.Line }) -join " "))
Log ("storage: " + ((Select-String -Path (Join-Path $Out "df.txt") -Pattern " /data$" | ForEach-Object { $_.Line }) -join " "))
Log ("display: " + ((Get-Content (Join-Path $Out "wm.txt")) -join " "))

# packages (inventory only)
Run "packages-all.txt" "pm list packages -f"
Run "packages-system.txt" "pm list packages -s"
Run "packages-user.txt" "pm list packages -3"
Run "packages-disabled.txt" "pm list packages -d"
Run "packages-enabled.txt" "pm list packages -e"
Run "packages-uninstalled-for-user.txt" "pm list packages -u"
Run "features.txt" "pm list features"
Log ("packages: total=" + (Get-Content (Join-Path $Out "packages-all.txt")).Count + " system=" + (Get-Content (Join-Path $Out "packages-system.txt")).Count + " user=" + (Get-Content (Join-Path $Out "packages-user.txt")).Count + " disabled=" + (Get-Content (Join-Path $Out "packages-disabled.txt")).Count)
Log "vendor-ish packages (tcl/tv/vision/ads):"
Select-String -Path (Join-Path $Out "packages-all.txt") -Pattern "tcl|\.tv\.|vision|ads|promo|recommend|analytic|report|stat" | ForEach-Object { ($_.Line -replace '.*=','') } | Sort-Object | Tee-Object -FilePath $Summary -Append

# launcher / home
Run "home-resolve.txt" "cmd package resolve-activity --brief -a android.intent.action.MAIN -c android.intent.category.HOME"
Run "home-candidates.txt" "cmd package query-activities --brief -a android.intent.action.MAIN -c android.intent.category.HOME"
Run "home-preferred.txt" "dumpsys package preferred-activities"
Run "window-focus.txt" "dumpsys window windows | grep -E 'mCurrentFocus|mFocusedApp'"
Run "activities-top.txt" "dumpsys activity activities | grep -E 'topResumedActivity|mResumedActivity|ResumedActivity|mFocusedApp'"
Run "role-home.txt" "cmd role get-role-holders android.app.role.HOME"
Log ("current HOME resolves to: " + (Get-Content (Join-Path $Out "home-resolve.txt") | Select-Object -Last 1))
Log "HOME candidates:"; Get-Content (Join-Path $Out "home-candidates.txt") | Where-Object { $_.Trim() -ne "" } | Tee-Object -FilePath $Summary -Append
Log ("HOME role holder: " + ((Get-Content (Join-Path $Out "role-home.txt")) -join " "))
Log ("focused window: " + ((Get-Content (Join-Path $Out "window-focus.txt")) -join " "))

# settings baseline (read-only)
Run "settings-global.txt" "settings list global"
Run "settings-system.txt" "settings list system"
Run "settings-secure.txt" "settings list secure"
Log ("animation scales: " + ((Select-String -Path (Join-Path $Out "settings-global.txt") -Pattern "animator_duration_scale|transition_animation_scale|window_animation_scale" | ForEach-Object { $_.Line }) -join " "))

# processes & performance baseline
Run "ps.txt" "ps -A"
Run "meminfo-summary.txt" "dumpsys meminfo | head -80"
Run "uptime.txt" "uptime; cat /proc/loadavg"
Log ("process count: " + ((Get-Content (Join-Path $Out "ps.txt")).Count - 1) + "  load: " + (Get-Content (Join-Path $Out "uptime.txt") | Select-Object -Last 1))
Log "top PSS (dumpsys meminfo):"; (Get-Content (Join-Path $Out "meminfo-summary.txt") | Select-String -Pattern "Total PSS by process" -Context 0,12 | ForEach-Object { $_.Line; $_.Context.PostContext }) | Tee-Object -FilePath $Summary -Append

# screenshot (binary-safe via exec-out)
$png = Join-Path $Out "screen-now.png"
$p = Start-Process -FilePath $Adb -ArgumentList @("-s",$Target,"exec-out","screencap","-p") -NoNewWindow -Wait -PassThru -RedirectStandardOutput $png -RedirectStandardError (Join-Path $Out "screencap.err")
if ((Test-Path $png) -and ((Get-Item $png).Length -gt 1000)) { Log "screenshot saved: $png ($((Get-Item $png).Length) bytes)" }
else { Log "screenshot FAILED (see screencap.err). Some firmware blocks screencap for protected content; retry with the home screen showing." }

& $Adb devices -l | Out-File (Join-Path $Out "adb-devices.txt")
Run "adb-shell-id.txt" "id"
Log ("adb shell identity: " + (Get-Content (Join-Path $Out "adb-shell-id.txt")))
Copy-Item $Summary "discovery\latest-summary.txt" -Force
Write-Host ""
Write-Host "DONE. Full output in $Out\. Paste the contents of discovery\latest-summary.txt into the chat, or commit the discovery folder."
