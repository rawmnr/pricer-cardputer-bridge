$ErrorActionPreference = "Stop"

# Explicit Windows host environment check
if ($env:OS -and $env:OS -notmatch "Windows") {
    Write-Warning "Target host environment is Windows. Running on non-Windows host may differ from recommended setup."
}

$RepoRoot = Split-Path -Parent $PSScriptRoot
$PcDir = Join-Path $RepoRoot "pc"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is not installed or not on PATH. Install it from https://docs.astral.sh/uv/"
}

Write-Host "Synchronizing Python environment via uv (idempotent)..."
uv sync --project $PcDir --all-groups

if (Get-Command pio -ErrorAction SilentlyContinue) {
    Write-Host "PlatformIO detected: $((pio --version) -join ' ')"
} else {
    Write-Warning "PlatformIO Core not found. Install it with pipx install platformio or use the VS Code extension."
}

Write-Host "Bootstrap complete."
