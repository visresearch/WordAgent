$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..\..")
$SourceDir = Join-Path $RepoRoot "backend\dist\wence_ai"
$OutputDir = Join-Path $RepoRoot "backend\package"
$IconFile = Join-Path $RepoRoot "packaging\robot.ico"
$IssFile = Join-Path $ScriptDir "wence_ai.iss"
$RawVersion = if ($env:APP_VERSION) { $env:APP_VERSION.TrimStart("v") } else { "0.0.0" }
# Inno Setup 的 AppVersion 只能使用数字版本号；预发布 tag（如
# 0.6.0-beta.1）保留在文件名/Release 中，安装器元数据使用 0.6.0.1。
if ($RawVersion -match '^(?<base>\d+\.\d+\.\d+)(?:-(?<prerelease>[^+]+))?(?:\+.*)?$') {
    $Version = $Matches['base']
    if ($Matches['prerelease']) {
        $iteration = [regex]::Match($Matches['prerelease'], '\d+$').Value
        if (-not $iteration) {
            $iteration = "1"
        }
        $Version = "$Version.$iteration"
    }
} else {
    throw "Invalid application version for Inno Setup: $RawVersion"
}
$OutputBaseFilename = "wence_ai-windows-x86_64-installer"

if (-not (Test-Path $SourceDir)) {
    throw "PyInstaller output not found: $SourceDir"
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$isccCommand = Get-Command ISCC.exe -ErrorAction SilentlyContinue
$isccPath = if ($isccCommand) { $isccCommand.Source } else { $null }
if (-not $isccPath) {
    $candidate = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    if (Test-Path $candidate) {
        $isccPath = $candidate
    }
}
if (-not $isccPath) {
    throw "ISCC.exe not found. Install Inno Setup 6 first."
}

& $isccPath `
    "/DAppVersion=$Version" `
    "/DSourceDir=$SourceDir" `
    "/DOutputDir=$OutputDir" `
    "/DOutputBaseFilename=$OutputBaseFilename" `
    "/DIconFile=$IconFile" `
    $IssFile

Write-Host "Created $(Join-Path $OutputDir "$OutputBaseFilename.exe")"
