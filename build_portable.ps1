$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $pythonCommand = Get-Command py -ErrorAction SilentlyContinue
    if ($pythonCommand) { $python = $pythonCommand.Source }
}
if (-not $python) { throw "Python was not found." }

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
New-Item (Join-Path $package "data\imports") -ItemType Directory -Force | Out-Null

$exe = Join-Path $package "ecompass.exe"
if (-not (Test-Path $exe)) { throw "Portable executable was not generated." }
$zip = Join-Path $distRoot "ecompass-portable.zip"
Remove-Item $zip -Force -ErrorAction SilentlyContinue
Compress-Archive -Path $package -DestinationPath $zip -CompressionLevel Optimal
Write-Host "Generated dist/ecompass-portable/ecompass.exe"
Write-Host "Generated dist/ecompass-portable.zip"
