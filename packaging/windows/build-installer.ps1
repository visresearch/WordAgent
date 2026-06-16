$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..\..")
$SourceDir = Join-Path $RepoRoot "backend\dist\wence_ai"
$OutputDir = Join-Path $RepoRoot "backend\package"
$IconFile = Join-Path $RepoRoot "packaging\robot.ico"
$IssFile = Join-Path $ScriptDir "wence_ai.iss"
$Version = if ($env:APP_VERSION) { $env:APP_VERSION.TrimStart("v") } else { "0.0.0" }
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
