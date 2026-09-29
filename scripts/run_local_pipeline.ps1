$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Pipeline = Join-Path $ProjectRoot "scripts\run_pipeline.py"
$LogDir = Join-Path $ProjectRoot "logs"
$LogFile = Join-Path $LogDir "local_pipeline.log"

Set-Location $ProjectRoot

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

"============================================================" | Out-File $LogFile -Append
"Pipeline started: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Out-File $LogFile -Append
"Project root: $ProjectRoot" | Out-File $LogFile -Append

if (-not (Test-Path $Python)) {
    "ERROR: Python executable not found: $Python" | Out-File $LogFile -Append
    exit 1
}

if (-not (Test-Path $Pipeline)) {
    "ERROR: Pipeline script not found: $Pipeline" | Out-File $LogFile -Append
    exit 1
}

Start-Sleep -Seconds 30

"Starting Python pipeline: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Out-File $LogFile -Append

& $Python $Pipeline 1>> $LogFile 2>&1

$ExitCode = $LASTEXITCODE

"Pipeline exit code: $ExitCode" | Out-File $LogFile -Append

if ($ExitCode -eq 0) {
    "Pipeline completed successfully." | Out-File $LogFile -Append
} else {
    "Pipeline FAILED." | Out-File $LogFile -Append
}

exit $ExitCode