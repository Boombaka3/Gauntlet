# C:\LLM Eval Harness\llm_eval_harness\bin\dev.ps1

$env:DOCKER_HOST = 'npipe:////./pipe/docker_engine'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location $projectRoot

Write-Host ''
Write-Host '=== EvidenceTrace -- Dev Mode ===' -ForegroundColor Cyan
Write-Host ('DOCKER_HOST = ' + $env:DOCKER_HOST)
Write-Host ''

# Step 1: Check stack is running; start it if not
try {
    $containerIds = docker-compose ps -q 2>&1
    $isRunning = $containerIds | Where-Object { $_ -match '\S' }
    if (-not $isRunning) {
        Write-Host 'Stack not running -- starting it now...' -ForegroundColor Yellow
        docker-compose up -d
        if ($LASTEXITCODE -ne 0) { throw ('docker-compose up -d exited with code ' + $LASTEXITCODE) }
        Write-Host 'Waiting 15 seconds for services...' -ForegroundColor Yellow
        Start-Sleep -Seconds 15
        Write-Host '[OK] Stack started' -ForegroundColor Green
    } else {
        Write-Host '[OK] Stack already running' -ForegroundColor Green
    }
} catch {
    Write-Host ('[FAIL] Could not start stack: ' + $_) -ForegroundColor Red
    Write-Host 'Run bin\start_stack.ps1 as Administrator first.' -ForegroundColor Yellow
    exit 1
}

# Step 2: Django dev server in a new window
Write-Host ''
Write-Host 'Opening Django dev server window...' -ForegroundColor Yellow
try {
    $q = "'"
    $djangoCmd = 'Set-Location ' + $q + $projectRoot + $q + '; $env:DOCKER_HOST = ' + $q + 'npipe:////./pipe/docker_engine' + $q + '; Write-Host ' + $q + 'Django dev server' + $q + ' -ForegroundColor Cyan; uv run python manage.py runserver'
    Start-Process powershell.exe -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-NoExit', '-Command', $djangoCmd)
    Write-Host '[OK] Django window opened' -ForegroundColor Green
} catch {
    Write-Host ('[FAIL] Could not open Django window: ' + $_) -ForegroundColor Red
    exit 1
}

# Step 3: Celery worker in a new window
Write-Host 'Opening Celery worker window...' -ForegroundColor Yellow
try {
    $q = "'"
    $celeryCmd = 'Set-Location ' + $q + $projectRoot + $q + '; $env:DOCKER_HOST = ' + $q + 'npipe:////./pipe/docker_engine' + $q + '; Write-Host ' + $q + 'Celery worker' + $q + ' -ForegroundColor Cyan; uv run celery -A config worker --loglevel=info --pool=solo'
    Start-Process powershell.exe -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-NoExit', '-Command', $celeryCmd)
    Write-Host '[OK] Celery window opened' -ForegroundColor Green
} catch {
    Write-Host ('[FAIL] Could not open Celery window: ' + $_) -ForegroundColor Red
    exit 1
}

# Step 4: Vite dev server in a new window
Write-Host 'Starting Vite dev server...' -ForegroundColor Cyan
try {
    $q = "'"
    $viteCmd = 'Set-Location ' + $q + $projectRoot + '\frontend' + $q + '; Write-Host ' + $q + 'Vite dev server' + $q + ' -ForegroundColor Cyan; npm run dev'
    Start-Process powershell.exe -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-NoExit', '-Command', $viteCmd)
    Write-Host '[OK] Vite window opened' -ForegroundColor Green
} catch {
    Write-Host ('[FAIL] Could not open Vite window: ' + $_) -ForegroundColor Red
}

Write-Host ''
Write-Host '=== Dev environment ready ===' -ForegroundColor Green
Write-Host ''
Write-Host '  Frontend: http://localhost:5173' -ForegroundColor White
Write-Host '  API:      http://localhost:8000/api/' -ForegroundColor White
Write-Host '  Health:   http://localhost:8000/api/health/' -ForegroundColor White
Write-Host '  MinIO:    http://localhost:9001  (minioadmin / minioadmin)' -ForegroundColor White
Write-Host '  Admin:    http://localhost:8000/admin/' -ForegroundColor White
Write-Host ''
Write-Host 'First-run checklist (if not done yet):' -ForegroundColor Yellow
Write-Host '  1. uv run python manage.py migrate_schemas --shared' -ForegroundColor DarkGray
Write-Host '  2. uv run python scripts/seed.py' -ForegroundColor DarkGray
Write-Host ''

