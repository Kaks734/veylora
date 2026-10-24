$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
if ($env:OS -ne 'Windows_NT') { throw 'Build the Windows executable on Windows.' }
python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
python -m pip install -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw 'Build dependency installation failed.' }
python -m PyInstaller --noconfirm --clean --onefile --console --noupx --name Veylora --add-data "static:static" app.py
if ($LASTEXITCODE -ne 0) { throw 'Executable build failed.' }
$package = Join-Path (Get-Location) 'release/Veylora-Windows'
New-Item -ItemType Directory -Force -Path $package | Out-Null
Copy-Item dist/Veylora.exe $package -Force
Copy-Item LICENSE, QUICKSTART.md, USAGE.md, COMPATIBILITY.md $package -Force
Get-FileHash "$package/Veylora.exe" -Algorithm SHA256 | ForEach-Object { "$($_.Hash.ToLower())  Veylora.exe" } | Set-Content "$package/SHA256SUMS.txt" -Encoding ascii
Compress-Archive -Path "$package/*" -DestinationPath release/Veylora-Windows.zip -Force
Write-Host 'Created release/Veylora-Windows.zip. Test this on a Windows computer before publishing.'
