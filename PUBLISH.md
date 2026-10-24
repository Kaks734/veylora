# Publish Veylora for other people

## 1. Upload the source
Create a public GitHub repository named `veylora`. Upload the CONTENTS of this project's folder at the repository root. The `.github/workflows/windows-build.yml` file must be present at that exact repository path; GitHub's file picker may hide dotfolders, so Git is preferred.

```powershell
git init
git add .
git commit -m "Veylora public release preparation"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/veylora.git
git push -u origin main
```

Replace YOUR_USERNAME with your account. If publishing into an existing repository, preserve its history and configure the correct remote rather than reinitializing blindly.

## 2. Build a Windows download
The Windows build workflow runs after a push to main. Or select Actions > Windows build > Run workflow. It tests the source, builds Veylora.exe and checks that the executable serves its UI. A successful run has a Veylora-Windows artifact containing the portable ZIP. Download it. A workflow artifact is not yet a published release.

You can also build on your own Windows computer with Python installed:

```powershell
python -m pip --version
powershell -NoProfile -File scripts/build_windows.ps1
powershell -NoProfile -File scripts/smoke_windows.ps1
```

Internet is required to install the build dependency. Users of the resulting EXE do not need Python. The build has not been executed on Windows in the preparation environment; the GitHub workflow must finish successfully before claiming an EXE is ready.

## 3. Test, then release
Test the packaged ZIP on a Windows machine. Verify source discovery, scan pause/resume, demo mode, label saving and your supported router separately. Publish a GitHub Release tagged v0.6.0 and attach release/Veylora-Windows.zip plus its SHA256SUMS.txt. Include COMPATIBILITY.md limits in the description. Once published, share your repository or release URL. Everyone can access a public release without your router account.

This workflow builds artifacts; it does not publish, modify repository access, request write tokens or automatically send invitations.

## Presentation
Suggested description: "A cinematic local network observatory for Windows, with live radar, device discovery and experimental HG8546M access controls. Created by Denis Kiriaku."
Topics: windows, python, network-monitoring, wifi, network-discovery, dashboard, open-source.

No official law-enforcement seals, government affiliation or certifications are claimed. The visual theme is fictional and independently branded. Name/domain/trademark availability has not been verified.
