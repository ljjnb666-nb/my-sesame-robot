param(
    [string]$Fqbn = "esp32:esp32:lolin_s2_mini",

    [string]$ArduinoJsonVersion = "6.21.5",

    [ValidateSet("none", "default", "more", "all")]
    [string]$Warnings = "default"
)

$ErrorActionPreference = "Stop"

# 获取仓库根目录
$RepoRoot = Split-Path -Parent $PSScriptRoot
$FirmwareDir = Join-Path $RepoRoot "firmware"
$MainSketch = Join-Path $FirmwareDir "sesame-firmware-main.ino"

# 检查 Arduino CLI
if (-not (Get-Command arduino-cli -ErrorAction SilentlyContinue)) {
    throw "未找到 arduino-cli，请检查 PATH 环境变量。"
}

# 检查固件主文件
if (-not (Test-Path $MainSketch)) {
    throw "未找到固件主文件：$MainSketch"
}

$Libraries = & arduino-cli lib list 2>$null
if ($LASTEXITCODE -ne 0 -or ($Libraries -notmatch "ArduinoJson")) {
    Write-Host "安装 ArduinoJson@$ArduinoJsonVersion ..."
    & arduino-cli lib install "ArduinoJson@$ArduinoJsonVersion"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "ArduinoJson 依赖安装失败，退出代码：$LASTEXITCODE"
        exit $LASTEXITCODE
    }
} else {
    Write-Host "已检测到 ArduinoJson 库。要求版本：$ArduinoJsonVersion"
}

# Arduino 要求主 ino 文件名和 sketch 文件夹名一致
$BuildRoot = Join-Path $RepoRoot ".build"
$SketchDir = Join-Path $BuildRoot "sesame-firmware-main"
$OutputDir = Join-Path $BuildRoot "output"

Remove-Item $SketchDir -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $OutputDir -Recurse -Force -ErrorAction SilentlyContinue

New-Item -ItemType Directory -Path $SketchDir -Force | Out-Null
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

# 复制 ino 和头文件到规范的临时 sketch 目录
Copy-Item $MainSketch $SketchDir

Get-ChildItem $FirmwareDir -Filter "*.h" | ForEach-Object {
    Copy-Item $_.FullName $SketchDir
}

Write-Host ""
Write-Host "========================================"
Write-Host " Sesame Firmware Build"
Write-Host "========================================"
Write-Host "开发板：$Fqbn"
Write-Host "固件目录：$FirmwareDir"
Write-Host "构建目录：$SketchDir"
Write-Host ""

& arduino-cli compile `
    --fqbn $Fqbn `
    --warnings $Warnings `
    --output-dir $OutputDir `
    $SketchDir

if ($LASTEXITCODE -ne 0) {
    Write-Error "固件编译失败，退出代码：$LASTEXITCODE"
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "固件编译成功。"
Write-Host "输出目录：$OutputDir"
