$ErrorActionPreference = 'Stop'
$taskProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath (Join-Path $taskProjectRoot 'frontend')
& npm.cmd run dev
