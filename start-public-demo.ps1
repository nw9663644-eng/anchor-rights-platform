$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend"
$LogsDir = Join-Path $Root "logs"
$FrontendPort = 8088
$BackendPort = 8000

New-Item -ItemType Directory -Force -Path $LogsDir | Out-Null

function Test-HttpOk($Url) {
  try {
    $response = Invoke-WebRequest $Url -UseBasicParsing -TimeoutSec 3
    return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
  } catch {
    return $false
  }
}

function Find-Cloudflared {
  $cmd = Get-Command cloudflared -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }

  $wingetPath = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet"
  $match = Get-ChildItem -Path $wingetPath -Recurse -Filter "cloudflared.exe" -ErrorAction SilentlyContinue |
    Select-Object -First 1
  if ($match) { return $match.FullName }

  throw "cloudflared was not found. Run: winget install --id Cloudflare.cloudflared -e"
}

if (-not (Test-HttpOk "http://127.0.0.1:$BackendPort/api/health")) {
  Write-Host "Starting backend..."
  Start-Process -FilePath powershell -WindowStyle Hidden -ArgumentList @(
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-Command",
    "Set-Location '$BackendDir'; .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port $BackendPort *> '$LogsDir\backend-public.log'"
  ) | Out-Null
}

if (-not (Test-HttpOk "http://127.0.0.1:$FrontendPort/api/health")) {
  Write-Host "Building and starting production frontend..."
  Push-Location $FrontendDir
  npm run build
  Pop-Location
  Start-Process -FilePath powershell -WindowStyle Hidden -ArgumentList @(
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-Command",
    "Set-Location '$Root'; node serve-public-demo.mjs *> '$LogsDir\frontend-public.log'"
  ) | Out-Null
}

Write-Host "Waiting for local services..."
for ($i = 0; $i -lt 30; $i++) {
  if (Test-HttpOk "http://127.0.0.1:$FrontendPort/api/health") { break }
  Start-Sleep -Seconds 1
}

if (-not (Test-HttpOk "http://127.0.0.1:$FrontendPort/api/health")) {
  throw "Frontend or backend did not start correctly. Check the logs directory."
}

$cloudflared = Find-Cloudflared
$TunnelLog = Join-Path $LogsDir ("cloudflared-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".log")

Write-Host "Starting Cloudflare tunnel..."
Start-Process -FilePath powershell -WindowStyle Hidden -ArgumentList @(
  "-NoProfile",
  "-ExecutionPolicy",
  "Bypass",
  "-Command",
  "& '$cloudflared' tunnel --url http://127.0.0.1:$FrontendPort *> '$TunnelLog'"
) | Out-Null

for ($i = 0; $i -lt 30; $i++) {
  Start-Sleep -Seconds 1
  if (Test-Path $TunnelLog) {
    $content = Get-Content $TunnelLog -Raw -Encoding UTF8
    if ([string]::IsNullOrWhiteSpace($content)) { continue }
    $match = [regex]::Match($content, "https://[a-z0-9-]+\.trycloudflare\.com")
    if ($match.Success) {
      Write-Host ""
      Write-Host "Public URL: $($match.Value)" -ForegroundColor Green
      Write-Host "Send this URL to others. Keep this computer, network, and services running."
      exit 0
    }
  }
}

throw "Could not get a public URL. Check $TunnelLog"
