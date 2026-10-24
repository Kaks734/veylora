# Veylora — Quick start
Created by Denis Kiriaku. Independent software, no government affiliation.

## Portable Windows release
1. Download Veylora-Windows.zip from this project's GitHub Releases, when a tested release has been published by the maintainer. This source archive does not contain a built executable.
2. Extract it, run Veylora.exe and keep its console open. It opens a local browser dashboard at http://127.0.0.1:8765. Close with Ctrl+C in the console.
3. Select your Wi-Fi interface. Click Scan my network or Start live monitoring. No router password is needed for discovery.
4. Router blocking is optional and supported only by the experimental Huawei HG8546M adapter. Other routers support discovery only. Read COMPATIBILITY.md.

The executable bundles Python. The source version requires Python 3.10+ and runs with start.bat or `py -3 app.py`.

## What the display means
- Responding: the device replied to the last local ICMP scan.
- Checking: a previously responding device missed one or two scans.
- Not responding: three scans missed. This is not proof of leaving Wi-Fi.
- Cached/unconfirmed: Windows remembers its address; presence was not confirmed.
- Radar positions are illustrative, not physical direction or distance.
- Activity is polling based: a 10-second pause between scans, plus scan duration.

Your data stays local, except DNS lookups use your configured DNS service. Labels and monitoring settings are retained under %LOCALAPPDATA%\NetPulse for compatibility with earlier releases. Router session cookies live in memory; passwords are not saved.

Use only networks you own or have permission to manage. An unsigned executable can show a Windows reputation warning; inspect the source, build it yourself, or use a release you trust. Do not disable your security software.
