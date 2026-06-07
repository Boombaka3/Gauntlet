# C:\LLM Eval Harness\llm_eval_harness\bin\start_stack.ps1

# Self-elevate to Administrator if not already elevated
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host 'Not running as Administrator -- relaunching elevated...'
    Start-Process powershell.exe -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $PSCommandPath) -Verb RunAs
    exit
}

$env:DOCKER_HOST = 'npipe:////./pipe/rancher-desktop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location $projectRoot

Write-Host ''
Write-Host '=== LLM Eval Harness -- Start Stack ===' -ForegroundColor Cyan
Write-Host ('DOCKER_HOST = ' + $env:DOCKER_HOST)
Write-Host ''

# Step 1: Strip the 'version:' line from docker-compose.yml
try {
    $composePath = Join-Path $projectRoot 'docker-compose.yml'
    $raw = [System.IO.File]::ReadAllText($composePath)
    if ($raw -match '(?m)^version:') {
        $raw = [System.Text.RegularExpressions.Regex]::Replace($raw, '(?m)^version:[^\r\n]*\r?\n', '')
        [System.IO.File]::WriteAllText($composePath, $raw, [System.Text.Encoding]::UTF8)
        Write-Host '[OK] Removed version line from docker-compose.yml' -ForegroundColor Green
    } else {
        Write-Host '[OK] docker-compose.yml has no version line to remove' -ForegroundColor Green
    }
} catch {
    Write-Host ('[FAIL] Could not patch docker-compose.yml: ' + $_) -ForegroundColor Red
    exit 1
}

# Step 2: Start containers
Write-Host ''
Write-Host 'Starting containers...' -ForegroundColor Yellow
try {
    docker-compose up -d
    if ($LASTEXITCODE -ne 0) { throw ('docker-compose up -d exited with code ' + $LASTEXITCODE) }
    Write-Host '[OK] Containers started' -ForegroundColor Green
} catch {
    Write-Host ('[FAIL] docker-compose up -d failed: ' + $_) -ForegroundColor Red
    exit 1
}

# Step 3: Wait for services to be ready
Write-Host ''
Write-Host 'Waiting 15 seconds for postgres / redis / minio...' -ForegroundColor Yellow
Start-Sleep -Seconds 15
Write-Host '[OK] Wait complete' -ForegroundColor Green

# Step 4: Preflight checks
Write-Host ''
Write-Host 'Running preflight checks...' -ForegroundColor Yellow
try {
    uv run python scripts/preflight.py
    if ($LASTEXITCODE -ne 0) { throw ('preflight.py exited with code ' + $LASTEXITCODE) }
    Write-Host '[OK] Preflight passed' -ForegroundColor Green
} catch {
    Write-Host ('[FAIL] Preflight failed: ' + $_) -ForegroundColor Red
    Write-Host 'Ensure Rancher Desktop is running and all containers are healthy.' -ForegroundColor Yellow
    exit 1
}

Write-Host ''
Write-Host '=== Stack is UP and healthy ===' -ForegroundColor Green
Write-Host ''
Write-Host '  API:    http://localhost:8000/api/' -ForegroundColor White
Write-Host '  MinIO:  http://localhost:9001' -ForegroundColor White
Write-Host '  Admin:  http://localhost:8000/admin/' -ForegroundColor White
Write-Host ''
Write-Host 'Run bin\dev.ps1 to start Django and Celery.' -ForegroundColor Cyan
Write-Host ''
