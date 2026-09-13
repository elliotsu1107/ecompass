$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $pythonCommand = Get-Command py -ErrorAction SilentlyContinue
    if ($pythonCommand) { $python = $pythonCommand.Source }
}
if (-not (Test-Path $python)) { throw "Python was not found. Create .venv and install requirements first." }

$buildRoot = Join-Path $Root "build\portable"
$distRoot = Join-Path $Root "dist"
$package = Join-Path $distRoot "ecompass-portable"
$pyinstallerDist = Join-Path $buildRoot "dist"
$pyinstallerWork = Join-Path $buildRoot "work"

Remove-Item $package -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $pyinstallerDist -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $pyinstallerWork -Recurse -Force -ErrorAction SilentlyContinue
New-Item $buildRoot, $distRoot -ItemType Directory -Force | Out-Null

$arguments = @(
    "-m", "PyInstaller",
    "--noconfirm", "--clean", "--onedir",
    "--name", "ecompass",
    "--distpath", $pyinstallerDist,
    "--workpath", $pyinstallerWork,
    "--add-data", "app\web\templates;app\web\templates",
    "--add-data", "app\web\static;app\web\static",
    "--add-data", "app\schema.sql;app",
    "run.py"
)
& $python $arguments
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }

New-Item $package -ItemType Directory -Force | Out-Null
Copy-Item (Join-Path $pyinstallerDist "ecompass\*") $package -Recurse -Force
Copy-Item (Join-Path $Root "start.bat") $package -Force
Copy-Item (Join-Path $Root "backup.bat") $package -Force
Copy-Item (Join-Path $Root "portable\README.txt") (Join-Path $package "README.txt") -Force

$exe = Join-Path $package "ecompass.exe"
if (-not (Test-Path $exe)) { throw "Portable executable was not generated." }
$zip = Join-Path $distRoot "ecompass-portable.zip"
Remove-Item $zip -Force -ErrorAction SilentlyContinue
Compress-Archive -Path $package -DestinationPath $zip -CompressionLevel Optimal

$verify = @'
from pathlib import Path
from zipfile import ZipFile
import sys
zip_path = Path(sys.argv[1])
with ZipFile(zip_path) as archive:
    names = [name.lower() for name in archive.namelist()]
forbidden = ("/docs/", "/data/", "/.git/", "__pycache__", ".pytest_cache", ".db", "secret.key", ".csv", ".xls", ".xlsx")
violations = [name for name in names if any(token in f"/{name}" for token in forbidden)]
if violations:
    raise SystemExit("Portable ZIP contains forbidden files: " + ", ".join(violations))
'@
$verify | & $python -c "import sys; exec(sys.stdin.read())" $zip
if ($LASTEXITCODE -ne 0) { throw "Portable ZIP privacy check failed." }
Write-Host "Generated dist/ecompass-portable/ecompass.exe"
Write-Host "Generated dist/ecompass-portable.zip"
