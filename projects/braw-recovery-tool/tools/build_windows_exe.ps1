$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

python -m PyInstaller `
  --name "BRAW Recovery" `
  --onefile `
  --windowed `
  --paths "$ProjectRoot\src" `
  --distpath "$ProjectRoot\dist" `
  --workpath "$ProjectRoot\build\pyinstaller" `
  --specpath "$ProjectRoot\build" `
  "$ProjectRoot\src\brawrec\gui.py"

Write-Host "Built: $ProjectRoot\dist\BRAW Recovery.exe"
