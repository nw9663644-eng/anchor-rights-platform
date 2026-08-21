$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$PackageRoot = Split-Path $PSScriptRoot -Parent
$InstallRoot = "C:\anchor-rights-platform"
$BackendRoot = Join-Path $InstallRoot "backend"
$LogRoot = Join-Path $InstallRoot "logs"
$BackupRoot = Join-Path $InstallRoot "backups"
$TaskName = "AnchorRightsPlatform"

function Write-Step([string]$Message) {
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Find-Python {
    $candidates = @(
        "C:\Python312\python.exe",
        "$env:ProgramFiles\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
    )
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) { return $candidate }
    }
    return $null
}

Write-Step "Preparing installation directories"
New-Item -ItemType Directory -Force -Path $InstallRoot, $LogRoot, $BackupRoot | Out-Null

$existingDb = Join-Path $BackendRoot "platform.db"
$existingEnv = Join-Path $BackendRoot ".env"
$existingDataKey = Join-Path $BackendRoot ".data_key"
$preserveRoot = Join-Path $env:TEMP "anchor-rights-preserve"
Remove-Item $preserveRoot -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $preserveRoot | Out-Null

foreach ($file in @($existingDb, $existingEnv, $existingDataKey)) {
    if (Test-Path $file) {
        Copy-Item $file -Destination $preserveRoot -Force
    }
}
if (Test-Path $existingDb) {
    Copy-Item $existingDb (Join-Path $BackupRoot ("platform-before-deploy-{0}.db" -f (Get-Date -Format "yyyyMMdd-HHmmss"))) -Force
}

Write-Step "Copying the latest platform files"
New-Item -ItemType Directory -Force -Path $BackendRoot, (Join-Path $InstallRoot "frontend") | Out-Null
Copy-Item (Join-Path $PackageRoot "backend\*") $BackendRoot -Recurse -Force
Copy-Item (Join-Path $PackageRoot "frontend\dist") (Join-Path $InstallRoot "frontend") -Recurse -Force

foreach ($name in @("platform.db", ".env", ".data_key")) {
    $preserved = Join-Path $preserveRoot $name
    if (Test-Path $preserved) {
        Copy-Item $preserved (Join-Path $BackendRoot $name) -Force
    }
}

$python = Find-Python
if (-not $python) {
    Write-Step "Installing Python 3.12"
    $installer = Join-Path $env:TEMP "python-3.12.10-amd64.exe"
    Invoke-WebRequest "https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe" -OutFile $installer
    Start-Process $installer -ArgumentList "/quiet InstallAllUsers=1 TargetDir=C:\Python312 PrependPath=1 Include_test=0" -Wait
    $python = Find-Python
}
if (-not $python) { throw "Python installation was not detected." }

Write-Step "Installing isolated backend dependencies"
$venvPython = Join-Path $InstallRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    & $python -m venv (Join-Path $InstallRoot ".venv")
}
& $venvPython -m pip install --disable-pip-version-check --upgrade pip
& $venvPython -m pip install --disable-pip-version-check -r (Join-Path $BackendRoot "requirements.txt")

Write-Step "Registering automatic startup and recovery"
$action = New-ScheduledTaskAction `
    -Execute $venvPython `
    -Argument "-m uvicorn app.main:app --host 0.0.0.0 --port 80 --workers 1" `
    -WorkingDirectory $BackendRoot
$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -StartWhenAvailable
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -User "SYSTEM" -RunLevel Highest -Force | Out-Null

if (-not (Get-NetFirewallRule -DisplayName "Anchor Rights Platform HTTP" -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName "Anchor Rights Platform HTTP" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow | Out-Null
}

$backupScript = @'
$ErrorActionPreference = "Stop"
$source = "C:\anchor-rights-platform\backend\platform.db"
$destination = "C:\anchor-rights-platform\backups"
New-Item -ItemType Directory -Force -Path $destination | Out-Null
if (Test-Path $source) {
    Copy-Item $source (Join-Path $destination ("platform-{0}.db" -f (Get-Date -Format "yyyyMMdd-HHmmss"))) -Force
}
Get-ChildItem $destination -Filter "platform-*.db" | Where-Object LastWriteTime -lt (Get-Date).AddDays(-30) | Remove-Item -Force
'@
$backupScriptPath = Join-Path $InstallRoot "backup-database.ps1"
Set-Content -Path $backupScriptPath -Value $backupScript -Encoding UTF8
$backupAction = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$backupScriptPath`""
$backupTrigger = New-ScheduledTaskTrigger -Daily -At 3am
Register-ScheduledTask -TaskName "AnchorRightsDatabaseBackup" -Action $backupAction -Trigger $backupTrigger -User "SYSTEM" -RunLevel Highest -Force | Out-Null

Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $venvPython } | Stop-Process -Force -ErrorAction SilentlyContinue
Start-ScheduledTask -TaskName $TaskName

Write-Step "Verifying the public service"
$healthy = $false
for ($attempt = 1; $attempt -le 30; $attempt++) {
    Start-Sleep -Seconds 2
    try {
        $health = Invoke-RestMethod "http://127.0.0.1/api/health" -TimeoutSec 5
        if ($health.status -eq "ok") {
            $healthy = $true
            Write-Host ("Platform is healthy. Version: {0}" -f $health.version) -ForegroundColor Green
            break
        }
    } catch {}
}
if (-not $healthy) {
    throw "The service did not pass its health check. Review Task Scheduler and $LogRoot."
}

Write-Host "Deployment completed: http://159.75.52.152" -ForegroundColor Green
