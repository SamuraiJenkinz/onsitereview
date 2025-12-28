# TQRS Windows Service Manager
# Run as Administrator

param(
    [ValidateSet("install", "start", "stop", "restart", "status", "uninstall")]
    [string]$Action = "install",
    [int]$Port = 8501,
    [string]$PythonPath = "C:\Python313\python.exe",
    [string]$AppPath = "C:\TQRS\src\tqrs\ui\app.py"
)

$TaskName = "TQRS"

switch ($Action) {
    "install" {
        # Remove existing task if present
        if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
            Write-Host "Removing existing task..."
            Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        }

        $action = New-ScheduledTaskAction `
            -Execute $PythonPath `
            -Argument "-m streamlit run `"$AppPath`" --server.headless true --server.address 0.0.0.0 --server.port $Port" `
            -WorkingDirectory (Split-Path $AppPath -Parent | Split-Path -Parent | Split-Path -Parent)

        $trigger = New-ScheduledTaskTrigger -AtStartup
        $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
        $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

        Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings | Out-Null

        Write-Host "TQRS installed on port $Port" -ForegroundColor Green
        Write-Host "URL: http://$($env:COMPUTERNAME):$Port"
    }
    "start" {
        Start-ScheduledTask -TaskName $TaskName
        Write-Host "TQRS started" -ForegroundColor Green
    }
    "stop" {
        Stop-ScheduledTask -TaskName $TaskName
        Write-Host "TQRS stopped" -ForegroundColor Yellow
    }
    "restart" {
        Stop-ScheduledTask -TaskName $TaskName
        Start-Sleep -Seconds 2
        Start-ScheduledTask -TaskName $TaskName
        Write-Host "TQRS restarted" -ForegroundColor Green
    }
    "status" {
        $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        if ($task) {
            $info = Get-ScheduledTaskInfo -TaskName $TaskName
            Write-Host "Task:   $TaskName"
            Write-Host "State:  $($task.State)"
            Write-Host "Last:   $($info.LastRunTime)"
            Write-Host "Result: $($info.LastTaskResult)"
        } else {
            Write-Host "TQRS not installed" -ForegroundColor Red
        }
    }
    "uninstall" {
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "TQRS uninstalled" -ForegroundColor Yellow
    }
}
