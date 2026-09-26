$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "Starting CityBike local pipeline..."
Write-Host "Project root: $ProjectRoot"

uv run python scripts/run_pipeline.py

$ExitCode = $LASTEXITCODE

if ($ExitCode -eq 0) {
    Write-Host "Pipeline completed successfully."
} else {
    Write-Error "Pipeline failed with exit code $ExitCode."
}

exit $ExitCode