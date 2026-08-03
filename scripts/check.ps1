$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$PcDir = Join-Path $RepoRoot "pc"
$FirmwareDir = Join-Path $RepoRoot "firmware"

uv run --project $PcDir ruff check $PcDir
uv run --project $PcDir ruff format --check $PcDir
uv run --project $PcDir mypy (Join-Path $PcDir "src")
uv run --project $PcDir pytest

if (Get-Command pio -ErrorAction SilentlyContinue) {
    pio run -d $FirmwareDir
} else {
    Write-Warning "Skipping firmware build because PlatformIO is not installed."
}
