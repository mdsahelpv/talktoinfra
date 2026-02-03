#!/usr/bin/env pwsh
# Test runner script for TalkAI Platform (Windows PowerShell version)
# This script runs all tests with real database connections via testcontainers

param(
    [switch]$Integration,
    [switch]$Coverage,
    [string]$Service = ""
)

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "TalkAI Platform Test Runner" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
try {
    $null = docker info 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Docker is not running. Please start Docker first." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "[ERROR] Docker is not running. Please start Docker first." -ForegroundColor Red
    exit 1
}

# Function to run tests for a service
function Run-ServiceTests {
    param([string]$ServiceName)
    
    $servicePath = "services\$ServiceName"
    
    if (-not (Test-Path $servicePath)) {
        Write-Host "[WARN] Service directory not found: $servicePath" -ForegroundColor Yellow
        return $false
    }
    
    if (-not (Test-Path "$servicePath\tests")) {
        Write-Host "[WARN] No tests directory found for $ServiceName" -ForegroundColor Yellow
        return $true
    }
    
    Write-Host "[INFO] Running tests for $ServiceName..." -ForegroundColor Green
    
    Push-Location $servicePath
    
    # Check if virtual environment exists
    if (-not (Test-Path "venv")) {
        Write-Host "[INFO] Creating virtual environment for $ServiceName..." -ForegroundColor Green
        python -m venv venv
    }
    
    # Activate virtual environment
    & .\venv\Scripts\Activate.ps1
    
    # Install dependencies
    Write-Host "[INFO] Installing dependencies for $ServiceName..." -ForegroundColor Green
    pip install -q -r requirements.txt
    pip install -q -r ..\..\requirements-test.txt 2>$null
    
    # Run tests
    $pytestArgs = @("-v", "--tb=short")
    
    if ($Coverage) {
        $pytestArgs += "--cov=app"
        $pytestArgs += "--cov-report=term-missing"
        $pytestArgs += "--cov-report=html:htmlcov"
    }
    
    if (-not $Integration) {
        $pytestArgs += "-m", "not integration"
    }
    
    Write-Host "[INFO] Executing: pytest $pytestArgs tests\" -ForegroundColor Green
    
    $testResult = $?
    try {
        pytest $pytestArgs tests\
        $testResult = $?
    } catch {
        $testResult = $false
    }
    
    deactivate
    Pop-Location
    
    if (-not $testResult) {
        Write-Host "[ERROR] Tests failed for $ServiceName" -ForegroundColor Red
        return $false
    }
    
    Write-Host "[INFO] Tests passed for $ServiceName" -ForegroundColor Green
    return $true
}

# Main execution
$failedServices = @()

if ($Service -ne "") {
    # Run tests for specific service
    if (-not (Run-ServiceTests -ServiceName $Service)) {
        $failedServices += $Service
    }
} else {
    # Run tests for all services with tests
    $serviceDirs = Get-ChildItem -Path "services" -Directory
    foreach ($dir in $serviceDirs) {
        $serviceName = $dir.Name
        
        if (Test-Path "$($dir.FullName)\tests") {
            if (-not (Run-ServiceTests -ServiceName $serviceName)) {
                $failedServices += $serviceName
            }
        }
    }
}

# Summary
Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Test Run Summary" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan

if ($failedServices.Count -eq 0) {
    Write-Host "[INFO] All tests passed!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "[ERROR] Tests failed for the following services:" -ForegroundColor Red
    foreach ($service in $failedServices) {
        Write-Host "  - $service" -ForegroundColor Red
    }
    exit 1
}
