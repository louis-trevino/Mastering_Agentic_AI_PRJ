<#
.SYNOPSIS
Starts the SuperGlasses FastAPI backend on port 8000.

.DESCRIPTION
Resolves the project directory from this script, uses the project virtual
environment directly, and starts the API with auto-reload enabled.
#>

$ErrorActionPreference = 'Stop'
$ProjectDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExecutable = Join-Path $ProjectDirectory '.venv\Scripts\python.exe'
$ApiModule = Join-Path $ProjectDirectory 'api.py'

if (-not (Test-Path -LiteralPath $PythonExecutable -PathType Leaf)) {
    throw "Python environment not found at '$PythonExecutable'. Run 'uv sync --all-groups' from the Categ_Eval_LangSmith directory."
}

if (-not (Test-Path -LiteralPath $ApiModule -PathType Leaf)) {
    throw "Backend module not found at '$ApiModule'."
}

Push-Location $ProjectDirectory
try {
    Write-Host "Starting SuperGlasses backend at http://localhost:8000"
    Write-Host "API documentation: http://localhost:8000/docs"
    & $PythonExecutable -m uvicorn api:app --reload --port 8000
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
