# TQRS (Incident Reviews) - Scheduled Task Setup Script
# Run as Administrator on Windows Server

param(
    [string]$AppPath = "D:\incidentreviews",
    [string]$Port = "8502",
    [string]$TaskName = "TQRS"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "TQRS - Incident Reviews Service Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check for admin rights
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Run this script as Administrator" -ForegroundColor Red
    exit 1
}

# Verify app path exists
if (-not (Test-Path "$AppPath\src\tqrs\ui\app.py")) {
    Write-Host "ERROR: app.py not found at $AppPath\src\tqrs\ui\" -ForegroundColor Red
    Write-Host "Clone the repo first: git clone https://github.com/mmctech/IncidentReviews.git" -ForegroundColor Yellow
    exit 1
}

# Verify venv exists
if (-not (Test-Path "$AppPath\venv\Scripts\python.exe")) {
    Write-Host "ERROR: Virtual environment not found at $AppPath\venv" -ForegroundColor Red
    Write-Host "Create venv first:" -ForegroundColor Yellow
    Write-Host "  python -m venv venv" -ForegroundColor White
    Write-Host "  venv\Scripts\pip install -e ." -ForegroundColor White
    exit 1
}


Write-Host "Configuration:" -ForegroundColor Green
Write-Host "  App Path:   $AppPath"
Write-Host "  Port:       $Port"
Write-Host "  Task Name:  $TaskName"
Write-Host ""

# Check if Azure OpenAI credentials are configured
$azureEndpoint = [Environment]::GetEnvironmentVariable("TQRS_AZURE_OPENAI_ENDPOINT", "Machine")
$azureApiKey = [Environment]::GetEnvironmentVariable("TQRS_AZURE_OPENAI_API_KEY", "Machine")
$azureDeployment = [Environment]::GetEnvironmentVariable("TQRS_AZURE_OPENAI_DEPLOYMENT", "Machine")

if ($azureEndpoint -and $azureApiKey -and $azureDeployment) {
    Write-Host "Azure OpenAI: CONFIGURED" -ForegroundColor Green
    Write-Host "  Credentials will be used automatically (hidden from users)" -ForegroundColor DarkGray
} else {
    Write-Host "Azure OpenAI: NOT CONFIGURED" -ForegroundColor Yellow
    Write-Host "  Users will need to enter API credentials manually." -ForegroundColor DarkGray
    Write-Host "  To configure server-side credentials, run:" -ForegroundColor DarkGray
    Write-Host "    .\configure_credentials.ps1 -Endpoint <url> -ApiKey <key> -Deployment <name>" -ForegroundColor Cyan
}
Write-Host ""

# Create startup batch script
$batchScript = @"
@echo off
cd /d $AppPath
call venv\Scripts\activate.bat
streamlit run src\tqrs\ui\app.py --server.address 0.0.0.0 --server.port $Port --server.headless true
"@

$batchPath = "$AppPath\start_server.bat"
Set-Content -Path $batchPath -Value $batchScript
Write-Host "Created startup script: $batchPath" -ForegroundColor Green

# Remove existing task if present
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "Removing existing scheduled task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Create scheduled task
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$batchPath`"" -WorkingDirectory $AppPath

$trigger = New-ScheduledTaskTrigger -AtStartup

$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -RestartCount 3 `
    -ExecutionTimeLimit (New-TimeSpan -Days 365)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description "TQRS - Ticket Quality Review System" | Out-Null

Write-Host "Scheduled task created: $TaskName" -ForegroundColor Green

# Start the task now
Write-Host ""
Write-Host "Starting the service..." -ForegroundColor Cyan
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 5

# Check if running
$task = Get-ScheduledTask -TaskName $TaskName
if ($task.State -eq "Running") {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "SUCCESS! Service is running" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    $hostname = [System.Net.Dns]::GetHostName()
    $ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike "*Loopback*" -and $_.IPAddress -notlike "169.*" } | Select-Object -First 1).IPAddress
    Write-Host "Access the app at:" -ForegroundColor Cyan
    Write-Host "  http://${hostname}:$Port" -ForegroundColor White
    if ($ip) {
        Write-Host "  http://${ip}:$Port" -ForegroundColor White
    }
} else {
    Write-Host "WARNING: Task may not have started. Check Task Scheduler." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Management commands:" -ForegroundColor Cyan
Write-Host "  .\manage_service.ps1 -Action status"
Write-Host "  .\manage_service.ps1 -Action stop"
Write-Host "  .\manage_service.ps1 -Action start"
Write-Host "  .\manage_service.ps1 -Action restart"
Write-Host "  .\manage_service.ps1 -Action remove"
