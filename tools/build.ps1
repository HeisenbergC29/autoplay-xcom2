#requires -Version 5.1
<#
.SYNOPSIS
Compile this script-only mod with the Windows War of the Chosen SDK.
.EXAMPLE
.\tools\build.ps1 -SdkPath 'D:\SteamLibrary\steamapps\common\XCOM 2 War of the Chosen SDK'
.EXAMPLE
.\tools\build.ps1 -SdkPath 'D:\WOTC SDK' -BuildBase -GamePath 'D:\Steam\steamapps\common\XCOM 2\XCom2-WarOfTheChosen'
.NOTES
Uses the same make / make -mods commandlets as X2CommunityCore/X2ModBuildCommon.
Reference: https://github.com/X2CommunityCore/X2ModBuildCommon (build_common.ps1).
Does not mirror or delete SDK-wide Development/Src, SrcOrig, or Script directories.
Do not run another build against the same SDK concurrently.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $SdkPath,
    [string] $GamePath,
    [switch] $BuildBase
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
    throw 'The WOTC compiler requires Windows. This is not a Linux build tool.'
}
$modName = 'AutoplayXCom2'
$repoRoot = Split-Path -Parent $PSScriptRoot
$projectRoot = Join-Path $repoRoot $modName
$SdkPath = (Resolve-Path -LiteralPath $SdkPath).Path
$compiler = Join-Path $SdkPath 'Binaries\Win64\XComGame.com'
$srcRoot = Join-Path $SdkPath 'Development\Src'
$srcOrig = Join-Path $SdkPath 'Development\SrcOrig'
$scriptRoot = Join-Path $SdkPath 'XComGame\Script'
$packageSrc = Join-Path $srcRoot $modName
$compiledPackage = Join-Path $scriptRoot "$modName.u"
$workRoot = Join-Path $repoRoot '.build'
# Use the same SDK mod layout as ModBuddy and X2ModBuildCommon, including mod
# configuration discovery by name, without relying on external staging support.
$stage = Join-Path $SdkPath "XComGame\Mods\$modName"
$distRoot = Join-Path $repoRoot 'dist'
$markerName = '.apx-build-owned'
$markerContents = 'AutoplayXCom2 build directory v1'

if (!(Test-Path -LiteralPath (Join-Path $projectRoot 'INSTALL.pl.md') -PathType Leaf)) {
    throw 'The project installation instructions are missing: AutoplayXCom2\INSTALL.pl.md.'
}
if (!(Test-Path -LiteralPath $compiler -PathType Leaf)) {
    throw "WOTC SDK compiler missing: $compiler. Install XCOM 2 War of the Chosen Development Tools from Steam (Windows)."
}
if (!(Test-Path -LiteralPath (Join-Path $srcRoot 'XComGame\Classes')) -and
    !(Test-Path -LiteralPath (Join-Path $srcOrig 'XComGame\Classes'))) {
    throw 'SDK UnrealScript sources missing. Expected Development\SrcOrig\XComGame\Classes or Development\Src\XComGame\Classes.'
}
if (!(Test-Path -LiteralPath (Join-Path $srcRoot 'Core\Globals.uci')) -and
    !(Test-Path -LiteralPath (Join-Path $srcOrig 'Core\Globals.uci'))) {
    throw 'SDK Core\Globals.uci is missing. Repair the WOTC SDK installation in Steam.'
}
if (!$BuildBase -and (!(Test-Path -LiteralPath (Join-Path $scriptRoot 'Core.u')) -or
                     !(Test-Path -LiteralPath (Join-Path $scriptRoot 'XComGame.u')))) {
    throw 'SDK base scripts have not been built. Build a project once in WOTC ModBuddy, or rerun this command with -BuildBase. The latter explicitly runs the SDK base-script compiler before compiling this mod.'
}

# Reset only a directory owned by this tool. Unknown local files are preserved.
function Reset-OwnedDirectory([string] $Path) {
    if (Test-Path -LiteralPath $Path) {
        $marker = Join-Path $Path $markerName
        if (!(Test-Path -LiteralPath $marker -PathType Leaf) -or
            ([IO.File]::ReadAllText($marker).Trim() -ne $markerContents)) {
            throw "Refusing to overwrite an unowned directory: $Path. Move it aside manually after preserving your files."
        }
        Remove-Item -LiteralPath $Path -Recurse -Force
    }
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
    [IO.File]::WriteAllText((Join-Path $Path $markerName), $markerContents)
}

# Never replace SDK base files or patches installed by the SDK owner.
function Copy-MissingSdkSources {
    if (!(Test-Path -LiteralPath $srcOrig -PathType Container)) { return }
    foreach ($file in Get-ChildItem -LiteralPath $srcOrig -Recurse -File) {
        if ($file.Extension -notin @('.uc', '.uci')) { continue }
        $relative = $file.FullName.Substring($srcOrig.Length).TrimStart('\', '/')
        $destination = Join-Path $srcRoot $relative
        if (!(Test-Path -LiteralPath $destination)) {
            New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
            Copy-Item -LiteralPath $file.FullName -Destination $destination
        }
    }
}

function Convert-LocalizationForGame([string] $LocalizationPath) {
    if (!(Test-Path -LiteralPath $LocalizationPath -PathType Container)) { return }
    foreach ($file in Get-ChildItem -LiteralPath $LocalizationPath -File -Recurse) {
        # ReadAllText detects an existing BOM, so repeating this conversion is
        # safe and never changes the repository's UTF-8 source localization.
        $contents = [IO.File]::ReadAllText($file.FullName, [Text.Encoding]::UTF8)
        [IO.File]::WriteAllText($file.FullName, $contents, [Text.Encoding]::Unicode)
    }
}

function Copy-ModPayload([string] $SourceRoot, [string] $Destination, [switch] $IncludeSource) {
    $entries = @('Config', 'Localization', "$modName.XComMod", 'INSTALL.pl.md')
    $entries += if ($IncludeSource) { 'Src' } else { 'Script' }
    # Check all required entries before copying a partial installation payload.
    foreach ($entry in $entries) {
        if (!(Test-Path -LiteralPath (Join-Path $SourceRoot $entry))) {
            throw "Required mod payload entry is missing: $entry in $SourceRoot"
        }
    }
    foreach ($entry in $entries) {
        Copy-Item -LiteralPath (Join-Path $SourceRoot $entry) -Destination $Destination -Recurse
    }
}

function Invoke-SdkMake([string[]] $Arguments, [string] $LogName) {
    $logPath = Join-Path $workRoot $LogName
    Push-Location (Split-Path -Parent $compiler)
    try {
        & $compiler @Arguments 2>&1 | Tee-Object -FilePath $logPath
        $compilerExitCode = $LASTEXITCODE
    }
    finally { Pop-Location }
    if ($compilerExitCode -ne 0) {
        throw "SDK compiler exited with code $compilerExitCode. See $logPath"
    }
    $logText = [IO.File]::ReadAllText($logPath)
    if ($logText -match '(?im)Crash Detected|^Failure\s*-|\b[1-9][0-9]* error\(s\)|\)\s*:\s*Error\b') {
        throw "SDK compiler reported an error despite its exit code. See $logPath"
    }
}

New-Item -ItemType Directory -Path $workRoot -Force | Out-Null
$lockPath = Join-Path $SdkPath 'Development\AutoplayXCom2.build.lock'
$buildLock = [IO.File]::Open($lockPath, [IO.FileMode]::OpenOrCreate,
                          [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
try {
    # Validate ownership before preparing files in either location.
    foreach ($path in @($packageSrc, $stage)) {
        if ((Test-Path -LiteralPath $path) -and
            (!(Test-Path -LiteralPath (Join-Path $path $markerName)) -or
             ([IO.File]::ReadAllText((Join-Path $path $markerName)).Trim() -ne $markerContents))) {
            throw "Build directory already exists without this tool's ownership marker: $path. Preserve/move it before retrying."
        }
    }
    Copy-MissingSdkSources
    if ($BuildBase) {
        Invoke-SdkMake -Arguments @('make', '-nopause', '-unattended') -LogName 'base-make.log'
    }
    Reset-OwnedDirectory $packageSrc
    Copy-Item -Path (Join-Path $projectRoot "Src\$modName\*") -Destination $packageSrc -Recurse
    Reset-OwnedDirectory $stage
    Copy-ModPayload $projectRoot $stage -IncludeSource
    # Keep source localization UTF-8 in Git; the game expects UTF-16LE with BOM.
    Convert-LocalizationForGame (Join-Path $stage 'Localization')
    # Preserve any old bytecode outside the SDK before forcing a fresh artifact.
    # It cannot accidentally satisfy the checks after a failed compiler invocation.
    if (Test-Path -LiteralPath $compiledPackage) {
        $previousRoot = Join-Path $workRoot 'previous'
        New-Item -ItemType Directory -Path $previousRoot -Force | Out-Null
        $previousName = '{0}-{1}.u' -f $modName, ([Guid]::NewGuid().ToString('N'))
        Copy-Item -LiteralPath $compiledPackage -Destination (Join-Path $previousRoot $previousName)
        Remove-Item -LiteralPath $compiledPackage -Force
    }
    $buildStarted = [DateTime]::UtcNow
    Invoke-SdkMake -Arguments @('make', '-nopause', '-mods', $modName, $stage) -LogName 'mod-make.log'
    if (!(Test-Path -LiteralPath $compiledPackage -PathType Leaf)) {
        throw "Compiler did not produce $compiledPackage. See .build\mod-make.log."
    }
    $packageInfo = Get-Item -LiteralPath $compiledPackage
    if ($packageInfo.Length -eq 0 -or $packageInfo.LastWriteTimeUtc -lt $buildStarted.AddSeconds(-2)) {
        throw 'Compiled package is empty or stale; refusing to package it.'
    }
    New-Item -ItemType Directory -Path (Join-Path $stage 'Script') -Force | Out-Null
    Copy-Item -LiteralPath $compiledPackage -Destination (Join-Path $stage 'Script')
    New-Item -ItemType Directory -Path $distRoot -Force | Out-Null
    $output = Join-Path $distRoot $modName
    Reset-OwnedDirectory $output
    Copy-ModPayload $stage $output
    $archive = Join-Path $distRoot "$modName.zip"
    if (Test-Path -LiteralPath $archive) { Remove-Item -LiteralPath $archive }
    Compress-Archive -LiteralPath $output -DestinationPath $archive
    Write-Host "Built: $archive"
    if ($GamePath) {
        $GamePath = (Resolve-Path -LiteralPath $GamePath).Path
        if (!(Test-Path -LiteralPath (Join-Path $GamePath 'Binaries\Win64\XCom2.exe'))) {
            throw 'GamePath must point to the XCom2-WarOfTheChosen directory containing Binaries\Win64\XCom2.exe.'
        }
        $installed = Join-Path $GamePath "XComGame\Mods\$modName"
        Reset-OwnedDirectory $installed
        Copy-Item -Path (Join-Path $output '*') -Destination $installed -Recurse
        Write-Host "Installed in: $installed"
    }
    Write-Host 'Compilation is not an in-game test. Enable the mod in your launcher and run the acceptance checklist.'
}
finally { $buildLock.Dispose() }
