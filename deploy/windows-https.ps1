param(
    [Parameter(Mandatory = $true)]
    [string]$PublicIp,

    [string]$InstallRoot = "C:\anchor-rights-platform"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$parsedIp = $null
if (-not [System.Net.IPAddress]::TryParse($PublicIp, [ref]$parsedIp)) {
    throw "PublicIp must be a valid IPv4 or IPv6 address."
}

$backendRoot = Join-Path $InstallRoot "backend"
$python = Join-Path $InstallRoot ".venv\Scripts\python.exe"
$lego = Join-Path $InstallRoot "https-tools\lego.exe"
$legoData = Join-Path $InstallRoot "lego-data"
$logRoot = Join-Path $InstallRoot "logs"
$taskName = "AnchorRightsHTTPS"

foreach ($required in @($backendRoot, $python, $lego)) {
    if (-not (Test-Path $required)) {
        throw "Required deployment component is missing: $required"
    }
}

New-Item -ItemType Directory -Force -Path $legoData, $logRoot | Out-Null

if (-not (Get-NetFirewallRule -DisplayName "Anchor Rights Platform HTTPS" -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName "Anchor Rights Platform HTTPS" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow | Out-Null
}

Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
Get-CimInstance Win32_Process |
    Where-Object { $_.Name -eq "python.exe" -and $_.CommandLine -match "--port 443" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

& $lego run `
    --accept-tos `
    --domains $PublicIp `
    --server letsencrypt `
    --profile shortlived `
    --tls `
    --path $legoData `
    --no-random-sleep 2>&1 |
    Tee-Object -FilePath (Join-Path $logRoot "lego-issue.log")
if ($LASTEXITCODE -ne 0) {
    throw "Certificate issuance failed. Check logs\lego-issue.log and confirm TCP 443 is publicly reachable."
}

$certificate = Join-Path $legoData "certificates\$PublicIp.crt"
$privateKey = Join-Path $legoData "certificates\$PublicIp.key"
foreach ($required in @($certificate, $privateKey)) {
    if (-not (Test-Path $required)) {
        throw "Certificate component is missing: $required"
    }
}

$runScriptPath = Join-Path $InstallRoot "run-https.ps1"
$runScript = @"
Set-Location "$backendRoot"
& "$python" -m uvicorn app.main:app --host 0.0.0.0 --port 443 --workers 1 --ssl-certfile "$certificate" --ssl-keyfile "$privateKey" *>> "$logRoot\https.log"
"@
Set-Content -Path $runScriptPath -Value $runScript -Encoding UTF8

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$runScriptPath`"" -WorkingDirectory $backendRoot
$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -StartWhenAvailable
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -User "SYSTEM" -RunLevel Highest -Force | Out-Null

$renewScriptPath = Join-Path $InstallRoot "renew-ip-certificate.ps1"
$renewScript = @"
`$ErrorActionPreference = "Continue"
Stop-ScheduledTask -TaskName "$taskName" -ErrorAction SilentlyContinue
Get-CimInstance Win32_Process | Where-Object { `$_.Name -eq "python.exe" -and `$_.CommandLine -match "--port 443" } | ForEach-Object { Stop-Process -Id `$_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 2
& "$lego" run --accept-tos --domains "$PublicIp" --server letsencrypt --profile shortlived --tls --path "$legoData" --no-random-sleep *>> "$logRoot\lego-renew.log"
Start-ScheduledTask -TaskName "$taskName"
"@
Set-Content -Path $renewScriptPath -Value $renewScript -Encoding UTF8

$renewAction = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$renewScriptPath`""
$renewTrigger = New-ScheduledTaskTrigger -Daily -DaysInterval 2 -At "03:20"
$renewSettings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 20) -StartWhenAvailable
Register-ScheduledTask -TaskName "AnchorRightsHTTPSRenewal" -Action $renewAction -Trigger $renewTrigger -Settings $renewSettings -User "SYSTEM" -RunLevel Highest -Force | Out-Null

Start-ScheduledTask -TaskName $taskName
$listening = $false
for ($attempt = 1; $attempt -le 30; $attempt++) {
    Start-Sleep -Seconds 2
    if (Get-NetTCPConnection -State Listen -LocalPort 443 -ErrorAction SilentlyContinue) {
        $listening = $true
        break
    }
}

if (-not $listening) {
    Get-Content (Join-Path $logRoot "https.log") -Tail 100 -ErrorAction SilentlyContinue
    throw "HTTPS did not start listening on TCP 443."
}

& curl.exe -k -sS "https://127.0.0.1/api/health"
Write-Host "HTTPS deployment completed: https://$PublicIp" -ForegroundColor Green
