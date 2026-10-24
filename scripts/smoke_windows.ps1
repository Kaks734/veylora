$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
$process = Start-Process -FilePath ./dist/Veylora.exe -ArgumentList '--no-browser' -PassThru
try {
    $ready = $false
    for ($i = 0; $i -lt 45; $i++) {
        if ($process.HasExited) { throw 'Executable exited unexpectedly.' }
        try {
            $state = Invoke-RestMethod http://127.0.0.1:8765/api/state -TimeoutSec 2
            $page = Invoke-WebRequest http://127.0.0.1:8765/ -UseBasicParsing -TimeoutSec 2
            if ($state.token -and $page.Content.Contains('VEYLORA')) { $ready = $true; break }
        } catch { Start-Sleep -Milliseconds 500 }
    }
    if (-not $ready) { throw 'Executable did not serve its bundled UI.' }
    Write-Host 'Windows executable starts and serves bundled assets.'
} finally {
    if (-not $process.HasExited) { Stop-Process -Id $process.Id -Force }
}
