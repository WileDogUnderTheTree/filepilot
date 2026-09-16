# FilePilot v0.1.0 一键测试脚本（PowerShell）
# 用法：pwsh -File tests/run_all_tests.ps1        （在任意目录下执行都可以）
#       pwsh -File tests/run_all_tests.ps1 -SkipPytest

param(
    [switch]$SkipPytest
)

$ErrorActionPreference = 'Continue'

# 项目根目录 = 本脚本所在目录的上一级
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

# 让 `python -m filepilot` / `import filepilot` 都可用
$env:PYTHONPATH = $ProjectRoot + [IO.Path]::PathSeparator + $env:PYTHONPATH
$env:PYTHONIOENCODING = 'utf-8'

# 找到可用的 Python 解释器
function Get-PythonExe {
    foreach ($candidate in @('python', 'py', 'python3')) {
        $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($cmd) { return $cmd.Source }
    }
    throw "未找到 Python 解释器，请先安装 Python 并加入 PATH"
}

$Python = Get-PythonExe
$Failures = @()

Write-Host "========================================"
Write-Host "FilePilot v0.1.0 测试"
Write-Host "Python : $Python"
Write-Host "根目录 : $ProjectRoot"
Write-Host "========================================"

# 0. 语法/导入自检
Write-Host "`n[0/3] 导入自检 ..."
& $Python -c "import filepilot, filepilot.cli, filepilot.scanner, filepilot.models; print('import ok, version', filepilot.__version__)"
if ($LASTEXITCODE -ne 0) { $Failures += '导入自检' }

# 1. unittest（标准库，零依赖）
Write-Host "`n[1/3] unittest ..."
& $Python -m unittest discover tests -v
if ($LASTEXITCODE -ne 0) { $Failures += 'unittest' }

# 2. pytest（装了才跑）
if (-not $SkipPytest) {
    Write-Host "`n[2/3] pytest ..."
    & $Python -m pytest tests -q
    if ($LASTEXITCODE -ne 0) { $Failures += 'pytest' }
}

# 3. 端到端冒烟测试（真实调用 python -m filepilot）
Write-Host "`n[3/3] E2E 冒烟测试 ..."
& $Python tests/smoke_e2e.py
if ($LASTEXITCODE -ne 0) { $Failures += 'smoke_e2e' }

Write-Host "`n========================================"
if ($Failures.Count -eq 0) {
    Write-Host "全部测试通过 [OK]"
    Write-Host "========================================"
    exit 0
} else {
    Write-Host ("失败的阶段: " + ($Failures -join ', '))
    Write-Host "========================================"
    exit 1
}
