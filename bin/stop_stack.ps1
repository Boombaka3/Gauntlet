# C:\LLM Eval Harness\llm_eval_harness\bin\stop_stack.ps1

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host 'Not running as Administrator -- relaunching elevated...'
    Start-Process powershell.exe -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $PSCommandPath) -Verb RunAs
    exit
}

$env:DOCKER_HOST = 'npipe:////./pipe/docker_engine'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location $projectRoot

Write-Host ''
Write-Host '=== EvidenceTrace -- Stop Stack ===' -ForegroundColor Cyan
Write-Host ('DOCKER_HOST = ' + $env:DOCKER_HOST)
Write-Host ''

try {
    docker-compose down
    if ($LASTEXITCODE -ne 0) { throw ('docker-compose down exited with code ' + $LASTEXITCODE) }
    Write-Host '[OK] All containers stopped and removed.' -ForegroundColor Green
} catch {
    Write-Host ('[FAIL] docker-compose down failed: ' + $_) -ForegroundColor Red
    exit 1
}

Write-Host ''

