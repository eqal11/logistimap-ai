$ErrorActionPreference = 'Stop'
$taskProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath (Join-Path $taskProjectRoot 'backend')
if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) { throw 'Create the backend virtual environment first; see DEVELOPMENT.md.' }
& ./.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
