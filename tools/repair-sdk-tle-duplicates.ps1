#requires -Version 5.1
<#
.SYNOPSIS
Report or quarantine byte-identical TLE classes duplicated in the SDK DLC_3 package.
.DESCRIPTION
Without -Apply this only reports a plan. With -Apply, all candidates must match
their TLE counterparts before anything moves. Only the eleven reported names
are eligible. Sources and old SDK DLC_3.u/TLE.u are retained in a unique backup
outside the SDK, with a local manifest. No compiler or game is launched.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $SdkPath,
    [string] $BackupRoot,
    [switch] $Apply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$classNames = @(
    'UIScreenListener_UICustomize_TLE',
    'X2Ability_TLE_Abilities',
    'X2Characters_TLE_Characters',
    'X2DownloadableContentInfo_DLC_TLE',
    'X2Helpers_DLC_TLE',
    'X2Item_TLE_Armor',
    'X2Item_TLE_QuestItems',
    'X2Item_TLE_Weapons',
    'X2MissionNarrative_DLC_TLE',
    'X2MissionSet_DLC_TLE',
    'X2StrategyElement_TLESoldierPersonalities'
)

function Get-FullDirectoryPath([string] $Path) {
    $full = [IO.Path]::GetFullPath(
        $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Path))
    if ($full -ne [IO.Path]::GetPathRoot($full)) {
        $full = $full.TrimEnd([char[]] @('\', '/'))
    }
    return $full
}

function Test-WithinPath([string] $Path, [string] $Parent) {
    $prefix = $Parent.TrimEnd([char[]] @('\', '/')) + [IO.Path]::DirectorySeparatorChar
    return $Path.Equals($Parent, [StringComparison]::OrdinalIgnoreCase) -or
        $Path.StartsWith($prefix,
            [StringComparison]::OrdinalIgnoreCase)
}

function Assert-NoReparsePath([string] $Path, [string] $Boundary) {
    $current = [IO.Path]::GetFullPath($Path)
    while ($true) {
        if (Test-Path -LiteralPath $current) {
            $item = Get-Item -LiteralPath $current -Force
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw "Refusing a symlink/junction in repair paths: $current"
            }
        }
        if ($current.Equals($Boundary, [StringComparison]::OrdinalIgnoreCase)) { break }
        $parent = Split-Path -Parent $current
        if ([string]::IsNullOrEmpty($parent) -or $parent -eq $current) {
            throw "Repair path is outside its expected boundary: $Path"
        }
        $current = $parent
    }
}

$resolvedSdk = Resolve-Path -LiteralPath $SdkPath
if ($resolvedSdk.Provider.Name -ne 'FileSystem') { throw 'SdkPath must use the filesystem provider.' }
$sdkRoot = Get-FullDirectoryPath $resolvedSdk.ProviderPath
Assert-NoReparsePath $sdkRoot ([IO.Path]::GetPathRoot($sdkRoot))
if (!(Test-Path -LiteralPath (Join-Path $sdkRoot 'Development') -PathType Container)) {
    throw 'SdkPath must be the SDK directory containing Development.'
}
$compilerPath = Join-Path $sdkRoot 'Binaries/Win64/XComGame.com'
Assert-NoReparsePath $compilerPath $sdkRoot
if (!(Test-Path -LiteralPath $compilerPath -PathType Leaf)) {
    throw 'SdkPath is not a WOTC SDK: Binaries/Win64/XComGame.com is missing.'
}
$hasSdkSources = $false
foreach ($tree in @('Src', 'SrcOrig')) {
    $coreClasses = Join-Path $sdkRoot ('Development/' + $tree + '/XComGame/Classes')
    if (Test-Path -LiteralPath $coreClasses -PathType Container) {
        Assert-NoReparsePath $coreClasses $sdkRoot
        $hasSdkSources = $true
    }
}
if (!$hasSdkSources) { throw 'WOTC SDK XComGame/Classes sources are missing.' }

$plan = @()
$sourceRootCount = 0
foreach ($tree in @('Src', 'SrcOrig')) {
    $treePath = Join-Path $sdkRoot ('Development/' + $tree)
    if (!(Test-Path -LiteralPath $treePath -PathType Container)) { continue }
    ++$sourceRootCount
    Assert-NoReparsePath $treePath $sdkRoot
    foreach ($name in $classNames) {
        $relative = 'Development/{0}/DLC_3/Classes/{1}.uc' -f $tree, $name
        $candidate = Join-Path $sdkRoot $relative
        if (!(Test-Path -LiteralPath $candidate)) { continue }
        $referenceRelative = 'Development/{0}/TLE/Classes/{1}.uc' -f $tree, $name
        $reference = Join-Path $sdkRoot $referenceRelative
        Assert-NoReparsePath $candidate $sdkRoot
        Assert-NoReparsePath $reference $sdkRoot
        if (!(Test-Path -LiteralPath $candidate -PathType Leaf) -or
            !(Test-Path -LiteralPath $reference -PathType Leaf)) {
            throw "Missing regular TLE counterpart for $relative; no files moved."
        }
        $hash = (Get-FileHash -LiteralPath $candidate -Algorithm SHA256).Hash
        if ($hash -ne (Get-FileHash -LiteralPath $reference -Algorithm SHA256).Hash) {
            throw "Different source versions: $relative and $referenceRelative; no files moved."
        }
        $plan += [pscustomobject] @{
            Kind = 'Source'; RelativePath = $relative; BackupRelativePath = $relative
            SHA256 = $hash; ReferenceRelativePath = $referenceRelative; Moved = $false
        }
    }
}
if ($sourceRootCount -eq 0) { throw 'SDK has neither Development/Src nor Development/SrcOrig.' }
$duplicateCount = $plan.Count

# No duplicates means no reason to invalidate otherwise healthy compiled SDK packages.
if ($duplicateCount -gt 0) {
    foreach ($package in @('DLC_3.u', 'TLE.u')) {
        $relative = 'XComGame/Script/' + $package
        $candidate = Join-Path $sdkRoot $relative
        if (!(Test-Path -LiteralPath $candidate)) { continue }
        Assert-NoReparsePath $candidate $sdkRoot
        if (!(Test-Path -LiteralPath $candidate -PathType Leaf)) {
            throw "SDK package is not a regular file: $relative"
        }
        $plan += [pscustomobject] @{
            Kind = 'Cache'; RelativePath = $relative; BackupRelativePath = $relative
            SHA256 = (Get-FileHash -LiteralPath $candidate -Algorithm SHA256).Hash
            ReferenceRelativePath = $null; Moved = $false
        }
    }
}
$cacheCount = $plan.Count - $duplicateCount
foreach ($entry in $plan) { Write-Host ('{0}: {1}' -f $entry.Kind, $entry.RelativePath) }

if (!$Apply -or $duplicateCount -eq 0) {
    $mode = 'Report'
    if ($Apply) { $mode = 'NoChanges' }
    Write-Host ('{0} identical duplicate sources; {1} SDK packages in plan. No files changed.' -f $duplicateCount, $cacheCount)
    [pscustomobject] @{
        Mode = $mode; SdkPath = $sdkRoot; DuplicateCount = $duplicateCount
        CacheCount = $cacheCount; BackupPath = $null; Files = $plan
    }
    return
}

if ([string]::IsNullOrWhiteSpace($BackupRoot)) {
    $documents = [Environment]::GetFolderPath('MyDocuments')
    if ([string]::IsNullOrWhiteSpace($documents)) {
        throw 'Documents directory is unavailable. Pass -BackupRoot outside the SDK.'
    }
    $BackupRoot = Join-Path $documents 'AutoplayXCom2-SdkBackups'
}
$backupBase = Get-FullDirectoryPath $BackupRoot
if (Test-WithinPath $backupBase $sdkRoot) { throw 'BackupRoot must be outside the SDK.' }
Assert-NoReparsePath $backupBase ([IO.Path]::GetPathRoot($backupBase))
if ((Test-Path -LiteralPath $backupBase) -and
    !(Test-Path -LiteralPath $backupBase -PathType Container)) {
    throw 'BackupRoot is not a directory.'
}

# Finish every read-only validation before creating even the backup directory.
foreach ($entry in $plan) {
    $source = Join-Path $sdkRoot $entry.RelativePath
    Assert-NoReparsePath $source $sdkRoot
    if (!(Test-Path -LiteralPath $source -PathType Leaf) -or
        (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash -ne $entry.SHA256) {
        throw "SDK changed during inspection: $($entry.RelativePath); no files moved."
    }
    if ($entry.Kind -eq 'Source') {
        $reference = Join-Path $sdkRoot $entry.ReferenceRelativePath
        if (!(Test-Path -LiteralPath $reference -PathType Leaf) -or
            (Get-FileHash -LiteralPath $reference -Algorithm SHA256).Hash -ne $entry.SHA256) {
            throw "TLE counterpart changed during inspection: $($entry.ReferenceRelativePath); no files moved."
        }
    }
}

$backup = Join-Path $backupBase ('SDK-TLE-' + [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $backup -Force | Out-Null
$manifestPath = Join-Path $backup 'manifest.json'
$manifest = [ordered] @{
    Version = 1; SdkPath = $sdkRoot; State = 'Planned'
    CreatedUtc = [DateTime]::UtcNow.ToString('o'); Files = $plan
}
function Write-RepairManifest {
    [IO.File]::WriteAllText($manifestPath, ($manifest | ConvertTo-Json -Depth 6), [Text.UTF8Encoding]::new($false))
}
Write-RepairManifest
$completed = @()
try {
    foreach ($entry in $plan) {
        $source = Join-Path $sdkRoot $entry.RelativePath
        $destination = Join-Path $backup $entry.BackupRelativePath
        Assert-NoReparsePath $source $sdkRoot
        if (!(Test-Path -LiteralPath $source -PathType Leaf) -or
            (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash -ne $entry.SHA256) {
            throw "SDK changed before moving $($entry.RelativePath)."
        }
        if ($entry.Kind -eq 'Source') {
            $reference = Join-Path $sdkRoot $entry.ReferenceRelativePath
            Assert-NoReparsePath $reference $sdkRoot
            if (!(Test-Path -LiteralPath $reference -PathType Leaf) -or
                (Get-FileHash -LiteralPath $reference -Algorithm SHA256).Hash -ne $entry.SHA256) {
                throw "TLE counterpart changed before moving $($entry.RelativePath)."
            }
        }
        New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
        Move-Item -LiteralPath $source -Destination $destination
        $entry.Moved = $true
        $completed += $entry
        Write-RepairManifest
    }
    $manifest.State = 'Applied'
    Write-RepairManifest
}
catch {
    $failure = $_
    $rollbackErrors = @()
    for ($i = $completed.Count - 1; $i -ge 0; --$i) {
        $entry = $completed[$i]
        try {
            $original = Join-Path $sdkRoot $entry.RelativePath
            if (Test-Path -LiteralPath $original) { throw 'Original path was recreated; preserved the backup.' }
            Move-Item -LiteralPath (Join-Path $backup $entry.BackupRelativePath) -Destination $original
            $entry.Moved = $false
        }
        catch { $rollbackErrors += ($entry.RelativePath + ': ' + $_.Exception.Message) }
    }
    $manifest.State = 'RolledBack'
    if ($rollbackErrors.Count -gt 0) { $manifest.State = 'RollbackIncomplete' }
    try { Write-RepairManifest } catch { Write-Warning ('Could not update manifest: ' + $_.Exception.Message) }
    throw ('Repair failed: {0}. Backup/manifest: {1}. Rollback issues: {2}' -f
        $failure.Exception.Message, $backup, ($rollbackErrors -join '; '))
}

Write-Host ('Quarantined {0} duplicate sources and {1} SDK packages. Backup: {2}' -f $duplicateCount, $cacheCount, $backup)
Write-Host 'Next: rebuild SDK base scripts, then the mod (tools/build.ps1 -SdkPath <SDK> -BuildBase). This tool did not launch the compiler.'
[pscustomobject] @{
    Mode = 'Applied'; SdkPath = $sdkRoot; DuplicateCount = $duplicateCount
    CacheCount = $cacheCount; BackupPath = $backup; Files = $plan
}
