$ErrorActionPreference = 'Stop'
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$port = '8080'
$rb = Join-Path $dir 'server_run.bat'
if (Test-Path $rb) { $m = [regex]::Match((Get-Content $rb -Raw), '--port (\d+)'); if ($m.Success) { $port = $m.Groups[1].Value } }
$in = Read-Host "Port number (just press Enter for $port)"
if ($in) { $port = $in.Trim() }

$cfg = Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -ne $null -and $_.NetAdapter.Status -eq 'Up' } | Select-Object -First 1
if (-not $cfg) { Write-Host '[ERROR] No active network connection found.'; exit 1 }
$ip = $cfg.IPv4Address.IPAddress
$pc = $env:COMPUTERNAME

$name = [regex]::Unescape('\uC6A9\uC811 \uC790\uACA9 \uD1B5\uD569 \uAD00\uB9AC')   # Korean shortcut name
function New-Url($path, $url) { Set-Content -Path $path -Value ("[InternetShortcut]`r`nURL=$url`r`n") -Encoding ASCII }

$out = Join-Path $dir 'shortcuts'
New-Item -ItemType Directory -Force -Path $out | Out-Null
New-Url (Join-Path $out "$name.url") "http://${ip}:$port"
New-Url (Join-Path $out "$name (PC name).url") "http://${pc}:$port"
New-Url (Join-Path $out "$name (this PC).url") "http://localhost:$port"

$placed = @()
foreach ($d in @([Environment]::GetFolderPath('Desktop'), 'C:\Users\Public\Desktop')) {
  try { if (Test-Path $d) { New-Url (Join-Path $d "$name.url") "http://localhost:$port"; $placed += $d } } catch {}
}

Write-Host ''
Write-Host '============================================================'
Write-Host " Shortcuts created in: $out"
Write-Host "   - $name.url               -> http://${ip}:$port   (copy this to OTHER PCs)"
Write-Host "   - $name (PC name).url     -> http://${pc}:$port   (works if names resolve on your network)"
Write-Host "   - $name (this PC).url     -> http://localhost:$port"
if ($placed.Count) { Write-Host " Desktop icon (for this PC) added to: $($placed -join ', ')" }
Write-Host ''
Write-Host ' NOTE: the IP address may change if your router assigns it automatically.'
Write-Host '       Ask IT to give this PC a fixed IP, or use the "PC name" shortcut.'
Write-Host '============================================================'
Start-Process $out
