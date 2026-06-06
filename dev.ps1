# C:\LLM Eval Harness\llm_eval_harness\dev.ps1

$env:DOCKER_HOST = "npipe:////./pipe/rancher-desktop"
Set-Location $PSScriptRoot

Write-Host ""
Write-Host "=== LLM Eval Harness -- Dev Mode ===" -ForegroundColor Cyan
Write-Host "DOCKER_HOST = $env:DOCKER_HOST"
Write-Host ""

# Step 1: Check stack is running; start it if not
try {
    $psOutput = docker-compose ps --services --filter "status=running" 2>&1
    $runningServices = $psOutput | Where-Object { $_ -match '\S' }
    if (-not $runningServices) {
        Write-Host "Stack not running -- starting it now..." -ForegroundColor Yellow
        docker-compose up -d
        if ($LASTEXITCODE -ne 0) { throw "docker-compose up -d failed" }
        Write-Host "Waiting 15 seconds for services..." -ForegroundColor Yellow
        Start-Sleep -Seconds 15
    } else {
        Write-Host "[OK] Stack already running: $($runningServices -join ', ')" -ForegroundColor Green
    }
} catch {
    Write-Host "[FAIL] Could not check/start stack: $_" -ForegroundColor Red
    Write-Host "Run start_stack.ps1 as Administrator first." -ForegroundColor Yellow
    exit 1
}

# Step 2: Django dev server in a new window
Write-Host ""
Write-Host "Opening Django dev server window..." -ForegroundColor Yellow
try {
    Start-Process powershell.exe -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-NoExit",
        "-Command",
        "Set-Location '$PSScriptRoot'; `$env:DOCKER_HOST='npipe:////./pipe/rancher-desktop'; Write-Host 'Django dev server' -ForegroundColor Cyan; uv run python manage.py runserver"
    )
    Write-Host "[OK] Django window opened" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] Could not open Django window: $_" -ForegroundColor Red
    exit 1
}

# Step 3: Celery worker in a new window
Write-Host "Opening Celery worker window..." -ForegroundColor Yellow
try {
    Start-Process powershell.exe -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-NoExit",
        "-Command",
        "Set-Location '$PSScriptRoot'; `$env:DOCKER_HOST='npipe:////./pipe/rancher-desktop'; Write-Host 'Celery worker' -ForegroundColor Cyan; uv run celery -A config worker --loglevel=info --pool=solo"
    )
    Write-Host "[OK] Celery window opened" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] Could not open Celery window: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== Dev environment ready ===" -ForegroundColor Green
Write-Host ""
Write-Host "  API docs:      http://localhost:8000/api/docs" -ForegroundColor White
Write-Host "  Health check:  http://localhost:8000/api/health/" -ForegroundColor White
Write-Host "  MinIO console: http://localhost:9001" -ForegroundColor White
Write-Host "  (user: minioadmin / minioadmin)" -ForegroundColor DarkGray
Write-Host ""
Write-Host "First-run checklist (if not done yet):" -ForegroundColor Yellow
Write-Host "  1. uv run python manage.py migrate_schemas --shared" -ForegroundColor DarkGray
Write-Host "  2. uv run python scripts/seed.py" -ForegroundColor DarkGray
Write-Host ""
