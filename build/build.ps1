# WenCe AI Windows 打包脚本

Write-Host "======================================"
Write-Host "  WenCe AI Windows 打包脚本"
Write-Host "======================================"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# 使用 Python 打包脚本
python build.py

Write-Host ""
Write-Host "打包完成！"
Write-Host "运行: .\dist\wence_ai.exe"
