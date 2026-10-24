# Veylora

**Independent network intelligence console for Windows.**  
**Created by Denis Kiriaku.**

A cinematic local dashboard with live radar, device discovery, names and labels, activity history, and experimental Huawei HG8546M blacklist controls. No government affiliation. Radar positions are illustrative.

## Run from source

1. Install Python 3.10 or newer with the Windows Python launcher.
2. Extract this source folder and double-click `start.bat`, or run `py -3 app.py`.
3. Your browser opens http://127.0.0.1:8765. Keep the console open; Ctrl+C stops the app.
4. Select your own Wi-Fi interface, then start a scan or live monitoring. Discovery does not need router credentials.
5. Optional: select the supported HG8546M profile, enter your own router administrator credentials locally, and provide your own Wi-Fi MAC as the protected adapter.

The router address field is populated from the selected network gateway after discovery. You can also enter the gateway manually. No personal router address, credentials or device list is bundled.

## Features and limits

- Automatic scans with a 10-second pause after completion.
- Device detection and loss-of-replies activity; three missed scans remove a previously responding device from the radar.
- Search, copy MAC addresses, manual labels and best-effort DNS names.
- Saved blacklist list, per-device unblock, and retained router sessions.
- Fictional demo mode for public screenshots.
- Localhost-only server, per-run request token and browser Origin/Host validation for changes.

Windows private IPv4 networks up to /24 are supported. Sleeping devices, blocked ICMP and client isolation can hide devices. Presence is based on replies, not authoritative Wi-Fi join/leave data. Router actions verify saved configuration; independently check whether device connectivity changed. Physical locations, packet interception and deauthentication are not features.

Blocking supports the experimental Huawei EchoLife HG8546M adapter only. Other routers support discovery only. Allowlist editing stays manual. The adapter does not automatically enable existing blacklist rules. See [COMPATIBILITY.md](COMPATIBILITY.md).

## Privacy

No personal credentials, session tokens, real MAC addresses, router captures or local settings are distributed. Tests and demo use synthetic examples. Your labels and monitoring preferences are stored outside the project under `%LOCALAPPDATA%\NetPulse` for backward compatibility. Passwords are not written to disk. Router cookies remain in server memory and are discarded on disconnect/restart. The captured router interface uses HTTP on the LAN. Hostname lookups use your configured DNS resolver.

Use demo mode for public screenshots. Do not upload your runtime data, router screenshots, captures, exports or credentials. The included `.gitignore` excludes common private and generated files, but cannot detect secrets embedded in otherwise valid source files. See [PRIVACY.md](PRIVACY.md).

## Share with others

This is a local Windows app. Each user runs their own copy and uses their own network and router account. Read [PUBLISH.md](PUBLISH.md) for the GitHub source upload, Windows executable build workflow and release steps. This source package contains no built EXE and has not been published to GitHub by this preparation step.

- [Quick start](QUICKSTART.md)
- [Compatibility](COMPATIBILITY.md)
- [Responsible use](USAGE.md)
- [Contributing](CONTRIBUTING.md)

## Development

```powershell
py -3 -m unittest discover -s tests -v
```

No runtime pip packages are needed. Build dependencies are separate in `requirements-build.txt`. The Windows executable workflow must succeed and the resulting package must be tested on Windows before redistribution. Node is optional for checking JavaScript syntax: `node --check static/app.js`.

## License

MIT. You may use, copy, modify, distribute, sublicense and sell copies, including commercially. Retain the copyright and permission notices in copies or substantial portions. Provided as is, without warranties; the full [LICENSE](LICENSE) governs. Responsible-use guidance is separate and adds no MIT conditions. The author credit in modified interfaces is optional; distribution of the copyright/license notices is required.
