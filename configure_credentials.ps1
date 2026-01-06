# TQRS - Azure OpenAI Credential Configuration Script
# Run as Administrator to set Machine-level environment variables
#
# Usage:
#   .\configure_credentials.ps1 -Endpoint "https://..." -ApiKey "..." -Deployment "gpt-4o"
#   .\configure_credentials.ps1 -Status          # Check current configuration
#   .\configure_credentials.ps1 -Clear           # Remove all credentials

param(
    [string]$Endpoint,
    [string]$ApiKey,
    [string]$Deployment,
    [string]$ApiVersion = "2024-02-15-preview",
    [switch]$Status,
    [switch]$Clear
)

# Environment variable names (with TQRS_ prefix)
$ENV_ENDPOINT = "TQRS_AZURE_OPENAI_ENDPOINT"
$ENV_API_KEY = "TQRS_AZURE_OPENAI_API_KEY"
$ENV_DEPLOYMENT = "TQRS_AZURE_OPENAI_DEPLOYMENT"
$ENV_API_VERSION = "TQRS_AZURE_OPENAI_API_VERSION"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "TQRS - Azure OpenAI Credential Manager" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check for admin rights
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Status check
if ($Status) {
    Write-Host "Current Configuration Status:" -ForegroundColor Green
    Write-Host ""

    $endpoint = [Environment]::GetEnvironmentVariable($ENV_ENDPOINT, "Machine")
    $apiKey = [Environment]::GetEnvironmentVariable($ENV_API_KEY, "Machine")
    $deployment = [Environment]::GetEnvironmentVariable($ENV_DEPLOYMENT, "Machine")
    $apiVersion = [Environment]::GetEnvironmentVariable($ENV_API_VERSION, "Machine")

    if ($endpoint) {
        Write-Host "  Endpoint:    $endpoint" -ForegroundColor White
    } else {
        Write-Host "  Endpoint:    (not set)" -ForegroundColor DarkGray
    }

    if ($apiKey) {
        # Mask the API key for display
        $masked = $apiKey.Substring(0, [Math]::Min(8, $apiKey.Length)) + "..." + $apiKey.Substring([Math]::Max(0, $apiKey.Length - 4))
        Write-Host "  API Key:     $masked" -ForegroundColor White
    } else {
        Write-Host "  API Key:     (not set)" -ForegroundColor DarkGray
    }

    if ($deployment) {
        Write-Host "  Deployment:  $deployment" -ForegroundColor White
    } else {
        Write-Host "  Deployment:  (not set)" -ForegroundColor DarkGray
    }

    if ($apiVersion) {
        Write-Host "  API Version: $apiVersion" -ForegroundColor White
    } else {
        Write-Host "  API Version: (not set, will use default)" -ForegroundColor DarkGray
    }

    Write-Host ""

    if ($endpoint -and $apiKey -and $deployment) {
        Write-Host "Status: CONFIGURED" -ForegroundColor Green
        Write-Host "Credentials will be used by TQRS automatically." -ForegroundColor White
    } else {
        Write-Host "Status: NOT CONFIGURED" -ForegroundColor Yellow
        Write-Host "Run with -Endpoint, -ApiKey, and -Deployment to configure." -ForegroundColor White
    }

    exit 0
}

# Clear credentials
if ($Clear) {
    Write-Host "Removing Azure OpenAI credentials..." -ForegroundColor Yellow

    [Environment]::SetEnvironmentVariable($ENV_ENDPOINT, $null, "Machine")
    [Environment]::SetEnvironmentVariable($ENV_API_KEY, $null, "Machine")
    [Environment]::SetEnvironmentVariable($ENV_DEPLOYMENT, $null, "Machine")
    [Environment]::SetEnvironmentVariable($ENV_API_VERSION, $null, "Machine")

    Write-Host ""
    Write-Host "Credentials removed." -ForegroundColor Green
    Write-Host ""
    Write-Host "NOTE: You must restart the TQRS service for changes to take effect:" -ForegroundColor Yellow
    Write-Host "  .\manage_service.ps1 -Action restart" -ForegroundColor White

    exit 0
}

# Validate required parameters for setting credentials
if (-not $Endpoint -or -not $ApiKey -or -not $Deployment) {
    Write-Host "Usage:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Set credentials:" -ForegroundColor White
    Write-Host "    .\configure_credentials.ps1 -Endpoint <url> -ApiKey <key> -Deployment <name>" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Check status:" -ForegroundColor White
    Write-Host "    .\configure_credentials.ps1 -Status" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Clear credentials:" -ForegroundColor White
    Write-Host "    .\configure_credentials.ps1 -Clear" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Parameters:" -ForegroundColor Yellow
    Write-Host "  -Endpoint      Azure OpenAI endpoint URL" -ForegroundColor White
    Write-Host "                 Example: https://your-resource.openai.azure.com/" -ForegroundColor DarkGray
    Write-Host "  -ApiKey        Azure OpenAI API key" -ForegroundColor White
    Write-Host "  -Deployment    Model deployment name" -ForegroundColor White
    Write-Host "                 Example: gpt-4o" -ForegroundColor DarkGray
    Write-Host "  -ApiVersion    API version (optional, default: 2024-02-15-preview)" -ForegroundColor White
    Write-Host ""
    exit 1
}

# Validate endpoint format
if (-not $Endpoint.StartsWith("https://")) {
    Write-Host "ERROR: Endpoint must start with https://" -ForegroundColor Red
    exit 1
}

# Trim trailing slash from endpoint for consistency
$Endpoint = $Endpoint.TrimEnd("/")

Write-Host "Setting Azure OpenAI credentials..." -ForegroundColor Cyan
Write-Host ""

# Set environment variables at Machine level
try {
    [Environment]::SetEnvironmentVariable($ENV_ENDPOINT, $Endpoint, "Machine")
    Write-Host "  Set $ENV_ENDPOINT" -ForegroundColor Green

    [Environment]::SetEnvironmentVariable($ENV_API_KEY, $ApiKey, "Machine")
    Write-Host "  Set $ENV_API_KEY" -ForegroundColor Green

    [Environment]::SetEnvironmentVariable($ENV_DEPLOYMENT, $Deployment, "Machine")
    Write-Host "  Set $ENV_DEPLOYMENT" -ForegroundColor Green

    [Environment]::SetEnvironmentVariable($ENV_API_VERSION, $ApiVersion, "Machine")
    Write-Host "  Set $ENV_API_VERSION" -ForegroundColor Green

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "SUCCESS! Credentials configured." -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Configuration Summary:" -ForegroundColor Cyan
    Write-Host "  Endpoint:    $Endpoint" -ForegroundColor White
    $masked = $ApiKey.Substring(0, [Math]::Min(8, $ApiKey.Length)) + "..." + $ApiKey.Substring([Math]::Max(0, $ApiKey.Length - 4))
    Write-Host "  API Key:     $masked" -ForegroundColor White
    Write-Host "  Deployment:  $Deployment" -ForegroundColor White
    Write-Host "  API Version: $ApiVersion" -ForegroundColor White
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "  1. If TQRS service is running, restart it:" -ForegroundColor White
    Write-Host "     .\manage_service.ps1 -Action restart" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  2. Or install the service if not already done:" -ForegroundColor White
    Write-Host "     .\setup_service.ps1 -Port 8502" -ForegroundColor Cyan
    Write-Host ""

} catch {
    Write-Host "ERROR: Failed to set environment variables" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
