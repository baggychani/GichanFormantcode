param(
    [switch]$SkipSync,
    [switch]$SkipRuff,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    # Older PowerShell hosts may not allow changing console encoding.
}

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not $env:UV_CACHE_DIR) {
    $env:UV_CACHE_DIR = Join-Path $ProjectRoot ".uv-cache"
}

if (-not $env:UV_PYTHON) {
    $LocalPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (Test-Path $LocalPython) {
        $env:UV_PYTHON = $LocalPython
    }
}

$LocalTmp = Join-Path $ProjectRoot ".tmp"
New-Item -ItemType Directory -Force -Path $LocalTmp | Out-Null
$env:TEMP = $LocalTmp
$env:TMP = $LocalTmp

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Command
    )

    Write-Host ""
    Write-Host "==> $Name" -ForegroundColor Cyan
    $global:LASTEXITCODE = 0
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

Invoke-Step "uv version" {
    uv --version
}

if (-not $SkipSync) {
    Invoke-Step "sync dependencies" {
        uv sync --locked --all-extras --dev
    }
}

Invoke-Step "version check" {
    if ($env:UV_PYTHON -and (Test-Path $env:UV_PYTHON)) {
        & $env:UV_PYTHON scripts/sync_version.py --check
    } else {
        uv run python scripts/sync_version.py --check
    }
}

if (-not $SkipRuff) {
    Invoke-Step "ruff check" {
        uv run ruff check .
    }
}

if (-not $SkipTests) {
    Invoke-Step "pytest" {
        $env:QT_QPA_PLATFORM = "offscreen"
        uv run pytest tests/ -q --basetemp .tmp/pytest -o cache_dir=.tmp/pytest_cache
    }
}

Write-Host ""
Write-Host "All requested checks completed." -ForegroundColor Green
