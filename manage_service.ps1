# TQRS (Incident Reviews) - Service Management Script

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("start", "stop", "restart", "status", "remove")]
    [string]$Action,

    [string]$TaskName = "TQRS"
)

switch ($Action) {
    "start" {
        Write-Host "Starting $TaskName..." -ForegroundColor Cyan
        Start-ScheduledTask -TaskName $TaskName
        Start-Sleep -Seconds 2
        $task = Get-ScheduledTask -TaskName $TaskName
        Write-Host "Status: $($task.State)" -ForegroundColor Green
    }
    "stop" {
        Write-Host "Stopping $TaskName..." -ForegroundColor Cyan
        Stop-ScheduledTask -TaskName $TaskName
        Start-Sleep -Seconds 2
        $task = Get-ScheduledTask -TaskName $TaskName
        Write-Host "Status: $($task.State)" -ForegroundColor Green
    }
    "restart" {
        Write-Host "Restarting $TaskName..." -ForegroundColor Cyan
        Stop-ScheduledTask -TaskName $TaskName
        Start-Sleep -Seconds 3
        Start-ScheduledTask -TaskName $TaskName
        Start-Sleep -Seconds 2
        $task = Get-ScheduledTask -TaskName $TaskName
        Write-Host "Status: $($task.State)" -ForegroundColor Green
    }
    "status" {
        $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        if ($task) {
            $info = Get-ScheduledTaskInfo -TaskName $TaskName
            Write-Host "Task:   $TaskName" -ForegroundColor Cyan
            Write-Host "State:  $($task.State)" -ForegroundColor Green
            Write-Host "Last:   $($info.LastRunTime)"
            Write-Host "Result: $($info.LastTaskResult)"
        } else {
            Write-Host "Task '$TaskName' not found. Run setup_service.ps1 first." -ForegroundColor Red
        }
    }
    "remove" {
        Write-Host "Removing $TaskName..." -ForegroundColor Yellow
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "Task removed" -ForegroundColor Green
    }
}
