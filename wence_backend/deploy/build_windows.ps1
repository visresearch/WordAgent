# Windows 打包脚本 - 支持 EXE 和 Installer
# 使用方法: .\build_windows.ps1 [-Type exe|installer|all]

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet('exe', 'installer', 'all')]
    [string]$Type = 'all'
)

$ErrorActionPreference = "Stop"

$VERSION = "0.1.0"
$APP_NAME = "wence-ai"
$BUILD_DIR = "dist"
$PACKAGE_DIR = "package"

Write-Host "==========================================`n" -ForegroundColor Green
Write-Host "WenCe AI Windows 打包工具`n" -ForegroundColor Green
Write-Host "版本: $VERSION`n" -ForegroundColor Green
Write-Host "==========================================`n" -ForegroundColor Green

function Print-Step {
    param([string]$Message)
    Write-Host "[步骤] $Message" -ForegroundColor Cyan
}

function Print-Warn {
    param([string]$Message)
    Write-Host "[警告] $Message" -ForegroundColor Yellow
}

function Print-Error {
    param([string]$Message)
    Write-Host "[错误] $Message" -ForegroundColor Red
}

function Check-Dependencies {
    Print-Step "检查依赖..."
    
    # 检查 Python
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Print-Error "Python 未安装或不在 PATH 中"
        exit 1
    }
    
    # 检查 uv
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Print-Warn "uv 未安装，将使用 pip"
        $script:USE_UV = $false
    } else {
        $script:USE_UV = $true
    }
    
    # 检查 NSIS（用于 installer）
    if ($Type -eq 'installer' -or $Type -eq 'all') {
        if (-not (Test-Path "C:\Program Files (x86)\NSIS\makensis.exe")) {
            Print-Warn "NSIS 未安装，将跳过 installer 构建"
            Print-Warn "下载地址: https://nsis.sourceforge.io/Download"
            $script:SKIP_INSTALLER = $true
        } else {
            $script:SKIP_INSTALLER = $false
            $script:MAKENSIS = "C:\Program Files (x86)\NSIS\makensis.exe"
        }
    }
}

function Install-Dependencies {
    Print-Step "安装 Python 依赖..."
    
    if ($USE_UV) {
        uv pip install -e ".[build]"
    } else {
        python -m pip install -e ".[build]"
    }
}

function Build-Binary {
    Print-Step "使用 PyInstaller 构建二进制文件..."
    
    # 清理旧文件
    if (Test-Path $BUILD_DIR) {
        Remove-Item -Recurse -Force $BUILD_DIR
    }
    if (Test-Path "build") {
        Remove-Item -Recurse -Force "build"
    }
    
    # 构建
    pyinstaller wence.spec --clean --noconfirm
    
    $exePath = Join-Path $BUILD_DIR "$APP_NAME.exe"
    if (Test-Path $exePath) {
        Write-Host "✓ 二进制文件构建成功: $exePath" -ForegroundColor Green
    } else {
        Print-Error "二进制文件构建失败"
        exit 1
    }
}

function Build-Installer {
    if ($SKIP_INSTALLER) {
        Print-Warn "跳过 Installer 构建（NSIS 未安装）"
        return
    }
    
    Print-Step "构建 Windows Installer..."
    
    # 创建 NSIS 脚本
    $nsiScript = @"
; WenCe AI Windows Installer Script
; 使用 NSIS (Nullsoft Scriptable Install System)

!define APP_NAME "WenCe AI"
!define APP_VERSION "$VERSION"
!define APP_PUBLISHER "WenCe AI Team"
!define APP_URL "https://github.com/yourusername/wence_ai"
!define APP_EXE "$APP_NAME.exe"

!include "MUI2.nsh"

; 安装程序基本信息
Name "`${APP_NAME}"
OutFile "$PACKAGE_DIR\wence-ai-$VERSION-setup.exe"
InstallDir "`$PROGRAMFILES64\`${APP_NAME}"
InstallDirRegKey HKLM "Software\`${APP_NAME}" "InstallDir"
RequestExecutionLevel admin

; 界面设置
!define MUI_ABORTWARNING
!define MUI_ICON "`${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_UNICON "`${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"

; 安装页面
!insertmacro MUI_PAGE_LICENSE "LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; 卸载页面
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; 语言
!insertmacro MUI_LANGUAGE "SimpChinese"
!insertmacro MUI_LANGUAGE "English"

; 安装部分
Section "MainSection" SEC01
    SetOutPath "`$INSTDIR"
    SetOverwrite on
    
    ; 复制文件
    File "$BUILD_DIR\$APP_NAME.exe"
    File /nonfatal ".env.example"
    File /nonfatal "README.md"
    
    ; 创建默认配置文件
    IfFileExists "`$INSTDIR\.env" +2 0
    CopyFiles /SILENT "`$INSTDIR\.env.example" "`$INSTDIR\.env"
    
    ; 创建开始菜单快捷方式
    CreateDirectory "`$SMPROGRAMS\`${APP_NAME}"
    CreateShortCut "`$SMPROGRAMS\`${APP_NAME}\`${APP_NAME}.lnk" "`$INSTDIR\`${APP_EXE}"
    CreateShortCut "`$SMPROGRAMS\`${APP_NAME}\配置文件.lnk" "`$INSTDIR\.env"
    CreateShortCut "`$SMPROGRAMS\`${APP_NAME}\卸载.lnk" "`$INSTDIR\Uninstall.exe"
    
    ; 创建桌面快捷方式
    CreateShortCut "`$DESKTOP\`${APP_NAME}.lnk" "`$INSTDIR\`${APP_EXE}"
    
    ; 写入注册表
    WriteRegStr HKLM "Software\`${APP_NAME}" "InstallDir" "`$INSTDIR"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\`${APP_NAME}" "DisplayName" "`${APP_NAME}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\`${APP_NAME}" "DisplayVersion" "`${APP_VERSION}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\`${APP_NAME}" "Publisher" "`${APP_PUBLISHER}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\`${APP_NAME}" "URLInfoAbout" "`${APP_URL}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\`${APP_NAME}" "UninstallString" "`$INSTDIR\Uninstall.exe"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\`${APP_NAME}" "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\`${APP_NAME}" "NoRepair" 1
    
    ; 创建卸载程序
    WriteUninstaller "`$INSTDIR\Uninstall.exe"
SectionEnd

; 卸载部分
Section "Uninstall"
    ; 删除文件
    Delete "`$INSTDIR\`${APP_EXE}"
    Delete "`$INSTDIR\.env.example"
    Delete "`$INSTDIR\.env"
    Delete "`$INSTDIR\README.md"
    Delete "`$INSTDIR\Uninstall.exe"
    
    ; 删除快捷方式
    Delete "`$SMPROGRAMS\`${APP_NAME}\*.*"
    RMDir "`$SMPROGRAMS\`${APP_NAME}"
    Delete "`$DESKTOP\`${APP_NAME}.lnk"
    
    ; 删除注册表
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\`${APP_NAME}"
    DeleteRegKey HKLM "Software\`${APP_NAME}"
    
    ; 删除安装目录
    RMDir "`$INSTDIR"
SectionEnd
"@
    
    # 写入 NSIS 脚本
    $nsiPath = "installer.nsi"
    $nsiScript | Out-File -FilePath $nsiPath -Encoding UTF8
    
    # 创建简单的 LICENSE 文件（如果不存在）
    if (-not (Test-Path "LICENSE.txt")) {
        @"
MIT License

Copyright (c) 2026 WenCe AI Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"@ | Out-File -FilePath "LICENSE.txt" -Encoding UTF8
    }
    
    # 创建输出目录
    New-Item -ItemType Directory -Force -Path $PACKAGE_DIR | Out-Null
    
    # 运行 NSIS
    & $MAKENSIS $nsiPath
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Installer 构建成功: $PACKAGE_DIR\wence-ai-$VERSION-setup.exe" -ForegroundColor Green
    } else {
        Print-Error "Installer 构建失败"
    }
    
    # 清理临时文件
    Remove-Item $nsiPath
}

function Copy-Executable {
    Print-Step "复制可执行文件..."
    
    New-Item -ItemType Directory -Force -Path $PACKAGE_DIR | Out-Null
    
    $srcExe = Join-Path $BUILD_DIR "$APP_NAME.exe"
    $dstExe = Join-Path $PACKAGE_DIR "wence-ai-$VERSION.exe"
    
    Copy-Item $srcExe $dstExe -Force
    
    Write-Host "✓ 可执行文件已复制: $dstExe" -ForegroundColor Green
}

# 主函数
function Main {
    try {
        Check-Dependencies
        Install-Dependencies
        Build-Binary
        
        switch ($Type) {
            'exe' {
                Copy-Executable
            }
            'installer' {
                Copy-Executable
                Build-Installer
            }
            'all' {
                Copy-Executable
                Build-Installer
            }
        }
        
        Write-Host "`n==========================================`n" -ForegroundColor Green
        Write-Host "构建完成！`n" -ForegroundColor Green
        Write-Host "==========================================`n" -ForegroundColor Green
        
        Get-ChildItem $PACKAGE_DIR | Format-Table Name, Length, LastWriteTime
        
    } catch {
        Print-Error "构建过程中出错: $_"
        exit 1
    }
}

Main
