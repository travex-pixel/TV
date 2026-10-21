# Enabling ADB on the TCL TV and connecting from your computer

ADB (Android Debug Bridge) is Google's official diagnostic connection. Nothing
here bypasses security: the TV shows an authorisation prompt and you approve it
with the remote.

## 1. Find the TV's IP address

On the TV: **Settings → Network & Internet → (your Wi-Fi name)** and note the
IP address, for example `192.168.1.42`. Your computer must be on the same
Wi-Fi network.

## 2. Turn on developer options on the TV

Google TV (TCL, Android 11 or newer):

1. **Settings → System → About**
2. Scroll to **Android TV OS build** and press OK on it **7 times** until the TV
   says you are a developer.
3. Go back to **Settings → System → Developer options**.
4. Turn on **USB debugging**. On TVs connected by Wi-Fi this also enables
   debugging over the network. If there is a separate **Network debugging** or
   **Wireless debugging** switch, turn that on too.

Older Android TV (version 9 or 10): the same steps live under
**Settings → Device Preferences → About → Build**, then
**Device Preferences → Developer options**.

If the TV asks "Allow USB debugging?" or shows a pairing code at any point,
read the next section before answering.

## 3. Install ADB on your computer

Download Google's official "SDK Platform-Tools" for your operating system from
<https://developer.android.com/tools/releases/platform-tools> and unzip it.
That folder contains `adb` (Windows: `adb.exe`). No other install is needed.

macOS users can instead run `brew install android-platform-tools` if Homebrew
is installed. Ubuntu/Debian users can run `sudo apt install adb`.

## 4. Connect

Open a terminal (Windows: PowerShell) in the unzipped platform-tools folder
and run, replacing the IP with your TV's:

```
adb connect 192.168.1.42:5555
```

The TV will show **"Allow USB debugging?"** with your computer's fingerprint.
Choose **Always allow from this computer** and **OK** with the remote. Then:

```
adb devices
```

should list the TV as `device`. If it says `unauthorized`, look at the TV
screen and accept the prompt. If it says `offline`, run
`adb disconnect` then `adb connect` again.

### If the TV uses "Wireless debugging" with a pairing code (Android 11+)

Open **Developer options → Wireless debugging → Pair device with pairing
code**. The TV shows an IP:port and a 6-digit code. Run:

```
adb pair 192.168.1.42:PORT
```

type the 6-digit code, then run `adb connect` with the IP and port shown on the
main Wireless debugging screen (the port differs from the pairing port).

## 5. Run the discovery script

See `tools/tv-discover.sh` (macOS/Linux) or `tools/tv-discover.ps1` (Windows).
Both are read-only: they only ask the TV questions and take a screenshot.

## Reconnecting later

The authorisation is remembered. After a TV reboot just run
`adb connect <TV-IP>:5555` again. If the TV ever stops accepting the
connection, toggle **USB debugging** off and on in Developer options.

## Turning it off afterwards

When the project is finished, turn **USB debugging** off in Developer options.
Leaving network debugging on means any device on your Wi-Fi could ask to
connect (each would still need approval on screen).
