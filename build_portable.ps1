# 构建 Windows 便携版：PyInstaller 打包 -> 组装目录 -> 压缩 -> 隐私门禁校验
# 用法: .\build_portable.ps1 [-SkipPyInstaller]
param(
    [switch]$SkipPyInstaller
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

# ---------------------------------------------------------------------------
# 原生命令封装
# PyInstaller 等工具会把正常日志写入 stderr；在 $ErrorActionPreference="Stop"
# 下 PowerShell 会把 stderr 视为 NativeCommandError 并直接终止脚本。
# 这里临时降级为 Continue、合并 stderr 并强制转成字符串，只以退出码判定成败。
# ---------------------------------------------------------------------------
function Invoke-Native {
    param(
        [Parameter(Mandatory = $true)][string]$Exe,
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$ExeArgs
    )
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & $Exe @ExeArgs 2>&1 | ForEach-Object { "$_" }
        $code = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previous
    }
    return @{ Code = $code; Output = $output }
}

function Write-Step($message) {
    Write-Host "[build] $message"
}

# ---------------------------------------------------------------------------
# 定位 Python
# ---------------------------------------------------------------------------
$python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pyLauncher) { $python = $pyLauncher.Source }
}
if (-not (Test-Path $python)) {
    throw "未找到 Python。请先创建 .venv 并安装 requirements.txt 与 requirements-build.txt。"
}
Write-Step "使用 Python: $python"

$buildRoot = Join-Path $Root "build\portable"
$distRoot = Join-Path $Root "dist"
$package = Join-Path $distRoot "ecompass-portable"
$pyinstallerDist = Join-Path $buildRoot "dist"
$pyinstallerWork = Join-Path $buildRoot "work"

foreach ($path in @($package, $pyinstallerDist, $pyinstallerWork)) {
    if (Test-Path $path) {
        try {
            Remove-Item $path -Recurse -Force -ErrorAction Stop
        }
        catch {
            throw "无法删除 $path。若 ecompass.exe 正在运行请先关闭，再重新构建。"
        }
    }
}
New-Item $buildRoot, $distRoot -ItemType Directory -Force | Out-Null

# ---------------------------------------------------------------------------
# 1. PyInstaller 打包
# ---------------------------------------------------------------------------
if ($SkipPyInstaller) {
    Write-Step "跳过 PyInstaller（-SkipPyInstaller）"
}
else {
    Write-Step "运行 PyInstaller（约需数分钟）..."
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
    $result = Invoke-Native -Exe $python -ExeArgs $arguments
    $result.Output | Where-Object { $_ -match "ERROR|Error|Traceback|failed" } | ForEach-Object { Write-Host $_ }
    if ($result.Code -ne 0) {
        ($result.Output | Select-Object -Last 25) | ForEach-Object { Write-Host $_ }
        throw "PyInstaller 构建失败（退出码 $($result.Code)）。上面是最后 25 行日志。"
    }
    Write-Step "PyInstaller 完成"
}

$bundle = Join-Path $pyinstallerDist "ecompass"
if (-not (Test-Path (Join-Path $bundle "ecompass.exe"))) {
    throw "未找到打包产物 $bundle\ecompass.exe。"
}

# ---------------------------------------------------------------------------
# 2. 组装便携目录
# ---------------------------------------------------------------------------
Write-Step "组装便携目录..."
New-Item $package -ItemType Directory -Force | Out-Null
Copy-Item (Join-Path $bundle "*") $package -Recurse -Force
Copy-Item (Join-Path $Root "start.bat") $package -Force
Copy-Item (Join-Path $Root "backup.bat") $package -Force
Copy-Item (Join-Path $Root "portable\README.txt") (Join-Path $package "README.txt") -Force

$exe = Join-Path $package "ecompass.exe"
if (-not (Test-Path $exe)) { throw "未生成便携版可执行文件。" }

# ---------------------------------------------------------------------------
# 3. 压缩
# 使用 .NET ZipFile 而非 Compress-Archive：后者在 PowerShell 5.1 下有 2GB 限制，
# 且对上千个小文件极慢。
# ---------------------------------------------------------------------------
Write-Step "压缩便携包..."
$zip = Join-Path $distRoot "ecompass-portable.zip"
Remove-Item $zip -Force -ErrorAction SilentlyContinue
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory(
    $package, $zip, [System.IO.Compression.CompressionLevel]::Optimal, $false
)
if (-not (Test-Path $zip)) { throw "压缩包未生成。" }

# ---------------------------------------------------------------------------
# 4. 隐私门禁：确认包内不含数据、文档与源码缓存
# ---------------------------------------------------------------------------
Write-Step "隐私门禁校验..."
$forbidden = @(
    "/docs/", "/data/", "/.git/", "__pycache__", ".pytest_cache",
    ".db", "secret.key", ".csv", ".xls", ".xlsx"
)
$violations = New-Object System.Collections.Generic.List[string]
$archive = $null
try {
    $archive = [System.IO.Compression.ZipFile]::OpenRead($zip)
    foreach ($entry in $archive.Entries) {
        $name = "/" + $entry.FullName.ToLowerInvariant()
        foreach ($token in $forbidden) {
            if ($name.Contains($token)) {
                $violations.Add($entry.FullName)
                break
            }
        }
    }
}
finally {
    if ($archive) { $archive.Dispose() }
}

if ($violations.Count -gt 0) {
    $violations | Select-Object -First 10 | ForEach-Object { Write-Host "  违规: $_" }
    throw "便携包包含 $($violations.Count) 个禁止文件，已中止。"
}

$sizeMb = [math]::Round((Get-Item $zip).Length / 1MB, 1)
Write-Host ""
Write-Host "Generated dist\ecompass-portable\ecompass.exe"
Write-Host "Generated dist\ecompass-portable.zip ($sizeMb MB)"
Write-Step "构建完成"
