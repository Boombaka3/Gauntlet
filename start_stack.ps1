# C:\LLM Eval Harness\llm_eval_harness\start_stack.ps1

# Auto-relaunch as Administrator if not already elevated
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Not running as Administrator -- relaunching elevated..."
    Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

$env:DOCKER_HOST = "npipe:////./pipe/rancher-desktop"
Set-Location $PSScriptRoot

Write-Host ""
Write-Host "=== LLM Eval Harness -- Start Stack ===" -ForegroundColor Cyan
Write-Host "DOCKER_HOST = $env:DOCKER_HOST"
Write-Host ""

# Step 1: Remove obsolete 'version' line from docker-compose.yml
try {
    $composePath = Join-Path $PSScriptRoot "docker-compose.yml"
    $content = Get-Content $composePath -Raw
    if ($content -match '(?m)^version:.*\r?\n') {
        $content = $content -replace '(?m)^version:.*\r?\n', ''
        Set-Content $composePath $content -NoNewline -Encoding utf8
        Write-Host "[OK] Removed obsolete 'version' line from docker-compose.yml" -ForegroundColor Green
    } else {
        Write-Host "[OK] docker-compose.yml already has no 'version' line" -ForegroundColor Green
    }
} catch {
    Write-Host "[FAIL] Could not patch docker-compose.yml: $_" -ForegroundColor Red
    exit 1
}

# Step 2: docker-compose up -d
Write-Host ""
Write-Host "Starting containers..." -ForegroundColor Yellow
try {
    docker-compose up -d
    if ($LASTEXITCODE -ne 0) { throw "docker-compose up -d exited with code $LASTEXITCODE" }
    Write-Host "[OK] Containers started" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] docker-compose up -d failed: $_" -ForegroundColor Red
    exit 1
}

# Step 3: Wait for services to be ready
Write-Host ""
Write-Host "Waiting 15 seconds for postgres/redis/minio to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 15
Write-Host "[OK] Wait complete" -ForegroundColor Green

# Step 4: Preflight checks
Write-Host ""
Write-Host "Running preflight checks..." -ForegroundColor Yellow
try {
    uv run python scripts/preflight.py
    if ($LASTEXITCODE -ne 0) { throw "preflight.py exited with code $LASTEXITCODE" }
    Write-Host "[OK] Preflight passed" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] Preflight failed: $_" -ForegroundColor Red
    Write-Host "Check that Rancher Desktop is running and containers are healthy." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "=== Stack is UP and healthy ===" -ForegroundColor Green
Write-Host "Next: run .\dev.ps1 to start the Django server and Celery worker."
Write-Host ""
