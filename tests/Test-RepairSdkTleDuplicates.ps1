#requires -Version 5.1
<#
.SYNOPSIS
Exercise the optional TLE duplicate repair using disposable SDK-shaped fixtures.
.DESCRIPTION
Checks report-only behavior, complete hash validation before moves, preserved
canonical sources, recoverable backups, idempotence and unsafe-path refusal.
No game, real SDK or compiler is used.
#>
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$repair = Join-Path $repoRoot 'tools/repair-sdk-tle-duplicates.ps1'
$tokens = $null
$parseErrors = $null
[void] [System.Management.Automation.Language.Parser]::ParseFile(
    $repair, [ref] $tokens, [ref] $parseErrors)
if ($parseErrors.Count -gt 0) {
    throw ('Repair helper has parser errors: ' + ($parseErrors.Message -join '; '))
}

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
$sourceTrees = @('Src', 'SrcOrig')
$fixtureRoot = Join-Path ([IO.Path]::GetTempPath()) ('APX TLE repair tests ' + [guid]::NewGuid().ToString('N'))
$junctionsToRemove = @()

function Assert-True([bool] $Condition, [string] $Message) {
    if (!$Condition) { throw $Message }
}

function Get-Hashes([string] $Directory) {
    $hashes = @{}
    foreach ($file in Get-ChildItem -LiteralPath $Directory -File -Recurse) {
        $relative = $file.FullName.Substring($Directory.Length).TrimStart('\', '/').Replace('\', '/')
        $hashes[$relative] = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
    }
    return $hashes
}

function Assert-HashesEqual([hashtable] $Expected, [hashtable] $Actual, [string] $Message) {
    Assert-True ($Expected.Count -eq $Actual.Count) ($Message + ': file count changed')
    foreach ($relative in $Expected.Keys) {
        Assert-True ($Actual.ContainsKey($relative) -and $Expected[$relative] -eq $Actual[$relative]) ($Message + ': ' + $relative)
    }
}

function New-CaseFixture([string] $Name) {
    $sdk = Join-Path (Join-Path $fixtureRoot $Name) 'SDK with spaces'
    New-Item -ItemType Directory -Path (Join-Path $sdk 'Binaries/Win64') -Force | Out-Null
    [IO.File]::WriteAllText((Join-Path $sdk 'Binaries/Win64/XComGame.com'), 'Synthetic fixture only; never execute this file.')
    foreach ($tree in $sourceTrees) {
        $treeRoot = Join-Path $sdk ('Development/' + $tree)
        foreach ($package in @('DLC_3', 'TLE', 'XComGame')) {
            New-Item -ItemType Directory -Path (Join-Path $treeRoot ($package + '/Classes')) -Force | Out-Null
        }
        foreach ($name in $classNames) {
            # Synthetic text only. Each tree may legitimately have a local SDK
            # patch, but its duplicate must match its own TLE counterpart.
            $text = 'class ' + $name + ' extends Object; // fixture ' + $tree
            foreach ($package in @('TLE', 'DLC_3')) {
                [IO.File]::WriteAllText((Join-Path $treeRoot ($package + '/Classes/' + $name + '.uc')), $text)
            }
        }
        [IO.File]::WriteAllText((Join-Path $treeRoot 'DLC_3/Classes/KeepShenSource.uc'), 'class KeepShenSource extends Object;')
        # A filename resembling TLE is not enough to authorize a move.
        [IO.File]::WriteAllText((Join-Path $treeRoot 'DLC_3/Classes/Unlisted_TLE_Source.uc'), 'class Unlisted_TLE_Source extends Object;')
    }
    $scriptRoot = Join-Path $sdk 'XComGame/Script'
    New-Item -ItemType Directory -Path $scriptRoot -Force | Out-Null
    foreach ($name in @('DLC_3.u', 'TLE.u', 'Core.u')) {
        [IO.File]::WriteAllBytes((Join-Path $scriptRoot $name), [byte[]] @(0, 1, 2, 11, 255))
    }
    return $sdk
}

try {
    $caseSdk = New-CaseFixture 'report and apply'
    $backupRoot = Join-Path $fixtureRoot 'external backups'
    $originalHashes = Get-Hashes $caseSdk

    # Merely inspecting an SDK must not create a backup or change any file.
    $reports = @(& $repair -SdkPath $caseSdk -BackupRoot $backupRoot)
    Assert-True ($reports.Count -eq 1) 'Report mode must return one structured result.'
    $report = $reports[0]
    Assert-True ($report.Mode -eq 'Report') 'Default invocation was not report-only.'
    Assert-True ($report.DuplicateCount -eq 22 -and $report.CacheCount -eq 2) 'Report did not describe the expected source and cache plan.'
    Assert-True ([string]::IsNullOrEmpty([string] $report.BackupPath)) 'Report-only mode reported an applied backup.'
    Assert-True (!(Test-Path -LiteralPath $backupRoot)) 'Report-only mode created a backup directory.'
    Assert-HashesEqual $originalHashes (Get-Hashes $caseSdk) 'Report-only mode changed the SDK'

    $results = @(& $repair -SdkPath $caseSdk -BackupRoot $backupRoot -Apply)
    Assert-True ($results.Count -eq 1) 'Apply must return one structured result.'
    $result = $results[0]
    Assert-True ($result.Mode -eq 'Applied') 'Repair did not apply the validated plan.'
    Assert-True ($result.DuplicateCount -eq 22 -and $result.CacheCount -eq 2) 'Unexpected applied move count.'
    Assert-True (Test-Path -LiteralPath $result.BackupPath -PathType Container) 'Backup directory is missing.'
    $manifestPath = Join-Path $result.BackupPath 'manifest.json'
    Assert-True (Test-Path -LiteralPath $manifestPath -PathType Leaf) 'Recovery manifest is missing.'
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    Assert-True ($manifest.State -eq 'Applied') 'Manifest does not identify the completed repair.'
    Assert-True ($manifest.SdkPath -eq (Resolve-Path -LiteralPath $caseSdk).ProviderPath) 'Manifest points to the wrong SDK.'
    Assert-True (@($manifest.Files).Count -eq 24) 'Recovery manifest does not cover every moved file.'
    foreach ($entry in $manifest.Files) {
        $relative = $entry.RelativePath.Replace('\', '/')
        Assert-True ($entry.Kind -in @('Source', 'Cache')) 'Manifest contains an unknown move category.'
        Assert-True ($relative -eq $entry.BackupRelativePath.Replace('\', '/')) 'Backup mapping changed a relative path.'
        Assert-True ($relative -notmatch '(^/|(^|/)\.\.(/|$)|:)') 'Manifest contains an escaping path.'
        Assert-True ($originalHashes.ContainsKey($relative)) ('Manifest identifies an unexpected source: ' + $relative)
        $backupFile = Join-Path $result.BackupPath $entry.BackupRelativePath
        Assert-True (Test-Path -LiteralPath $backupFile -PathType Leaf) ('Backed-up file missing: ' + $relative)
        $backupHash = (Get-FileHash -LiteralPath $backupFile -Algorithm SHA256).Hash
        Assert-True ($backupHash -eq $originalHashes[$relative] -and $entry.SHA256 -eq $backupHash) ('Backup bytes differ: ' + $relative)
        Assert-True (!(Test-Path -LiteralPath (Join-Path $caseSdk $entry.RelativePath))) ('Moved file remains in SDK: ' + $relative)
    }
    $afterHashes = Get-Hashes $caseSdk
    Assert-True ($afterHashes.Count -eq $originalHashes.Count - 24) 'Repair moved more than the planned files.'
    foreach ($relative in $afterHashes.Keys) {
        Assert-True ($originalHashes.ContainsKey($relative) -and $afterHashes[$relative] -eq $originalHashes[$relative]) ('Unrelated or canonical source changed: ' + $relative)
    }
    foreach ($tree in $sourceTrees) {
        foreach ($name in $classNames) {
            Assert-True (Test-Path -LiteralPath (Join-Path $caseSdk ('Development/' + $tree + '/TLE/Classes/' + $name + '.uc'))) 'Canonical TLE file was moved.'
        }
        Assert-True (Test-Path -LiteralPath (Join-Path $caseSdk ('Development/' + $tree + '/DLC_3/Classes/KeepShenSource.uc'))) 'Real DLC_3 source was moved.'
        Assert-True (Test-Path -LiteralPath (Join-Path $caseSdk ('Development/' + $tree + '/DLC_3/Classes/Unlisted_TLE_Source.uc'))) 'Repair used a broad TLE filename pattern.'
    }

    # If the SDK compiler later regenerates caches, another repair with no
    # duplicate sources must leave those new packages and the backup alone.
    [IO.File]::WriteAllText((Join-Path $caseSdk 'XComGame/Script/DLC_3.u'), 'regenerated DLC_3 cache')
    [IO.File]::WriteAllText((Join-Path $caseSdk 'XComGame/Script/TLE.u'), 'regenerated TLE cache')
    $repeatHashes = Get-Hashes $caseSdk
    $backupCount = @(Get-ChildItem -LiteralPath $backupRoot -Directory).Count
    $repeat = & $repair -SdkPath $caseSdk -BackupRoot $backupRoot -Apply
    Assert-True ($repeat.Mode -eq 'NoChanges' -and $repeat.DuplicateCount -eq 0) 'Repeat invocation was not a no-op.'
    Assert-True ([string]::IsNullOrEmpty([string] $repeat.BackupPath)) 'No-op invocation created a new backup.'
    Assert-True (@(Get-ChildItem -LiteralPath $backupRoot -Directory).Count -eq $backupCount) 'No-op invocation added a backup directory.'
    Assert-HashesEqual $repeatHashes (Get-Hashes $caseSdk) 'No-op invocation touched new compiled packages'

    # A mismatch in the final candidate must prevent even the earlier valid
    # candidates or compiled packages from moving.
    $caseSdk = New-CaseFixture 'late hash mismatch'
    $backupRoot = Join-Path $fixtureRoot 'mismatch backups'
    $mismatch = Join-Path $caseSdk 'Development/SrcOrig/DLC_3/Classes/X2StrategyElement_TLESoldierPersonalities.uc'
    [IO.File]::AppendAllText($mismatch, ' // different patch')
    $beforeMismatch = Get-Hashes $caseSdk
    $refused = $false
    try { & $repair -SdkPath $caseSdk -BackupRoot $backupRoot -Apply | Out-Null } catch { $refused = $true }
    Assert-True $refused 'A differing SDK patch was accepted as an identical duplicate.'
    Assert-HashesEqual $beforeMismatch (Get-Hashes $caseSdk) 'Hash mismatch caused a partial repair'
    Assert-True (!(Test-Path -LiteralPath $backupRoot)) 'Hash mismatch created a backup before validating the full plan.'

    $caseSdk = New-CaseFixture 'inside SDK backup'
    $beforeInside = Get-Hashes $caseSdk
    $insideBackup = Join-Path $caseSdk 'unsafe backups'
    $refused = $false
    try { & $repair -SdkPath $caseSdk -BackupRoot $insideBackup -Apply | Out-Null } catch { $refused = $true }
    Assert-True $refused 'Repair accepted a backup inside the SDK.'
    Assert-HashesEqual $beforeInside (Get-Hashes $caseSdk) 'Invalid backup path caused changes'
    Assert-True (!(Test-Path -LiteralPath $insideBackup)) 'Invalid backup path was created.'

    $caseSdk = New-CaseFixture 'missing canonical'
    $backupRoot = Join-Path $fixtureRoot 'missing canonical backups'
    Remove-Item -LiteralPath (Join-Path $caseSdk 'Development/SrcOrig/TLE/Classes/X2StrategyElement_TLESoldierPersonalities.uc')
    $beforeMissing = Get-Hashes $caseSdk
    $refused = $false
    try { & $repair -SdkPath $caseSdk -BackupRoot $backupRoot -Apply | Out-Null } catch { $refused = $true }
    Assert-True $refused 'Repair accepted a duplicate without its canonical TLE source.'
    Assert-HashesEqual $beforeMissing (Get-Hashes $caseSdk) 'Missing canonical source caused changes'
    Assert-True (!(Test-Path -LiteralPath $backupRoot)) 'Missing canonical source created a backup.'

    $caseSdk = New-CaseFixture 'not an SDK'
    Remove-Item -LiteralPath (Join-Path $caseSdk 'Binaries/Win64/XComGame.com')
    [IO.File]::WriteAllText((Join-Path $caseSdk 'Binaries/Win64/XCom2.exe'), 'Synthetic game-shaped decoy; never execute.')
    $backupRoot = Join-Path $fixtureRoot 'not SDK backups'
    $beforeNonSdk = Get-Hashes $caseSdk
    $refused = $false
    try { & $repair -SdkPath $caseSdk -BackupRoot $backupRoot -Apply | Out-Null } catch { $refused = $true }
    Assert-True $refused 'Repair accepted a game-shaped directory without the SDK compiler.'
    Assert-HashesEqual $beforeNonSdk (Get-Hashes $caseSdk) 'Non-SDK directory was changed'
    Assert-True (!(Test-Path -LiteralPath $backupRoot)) 'Non-SDK directory created a backup.'

    # Junctions need no administrator privilege on ordinary Windows NTFS.
    # Their availability is reported explicitly on other hosts/filesystems.
    $caseSdk = New-CaseFixture 'junction source'
    $externalClasses = Join-Path $fixtureRoot 'external source classes'
    New-Item -ItemType Directory -Path $externalClasses -Force | Out-Null
    $sourceLink = Join-Path $caseSdk 'Development/Src/DLC_3/Classes'
    Remove-Item -LiteralPath $sourceLink -Recurse -Force
    [IO.File]::WriteAllText((Join-Path $externalClasses 'X2Ability_TLE_Abilities.uc'),
        [IO.File]::ReadAllText((Join-Path $caseSdk 'Development/Src/TLE/Classes/X2Ability_TLE_Abilities.uc')))
    $junctionAvailable = $false
    try {
        New-Item -ItemType Junction -Path $sourceLink -Target $externalClasses -ErrorAction Stop | Out-Null
        $junctionsToRemove += $sourceLink
        $junctionAvailable = $true
    }
    catch { Write-Host ('SKIP: junction fixtures unavailable: ' + $_.Exception.Message) }
    if ($junctionAvailable) {
        $externalHash = (Get-FileHash -LiteralPath (Join-Path $externalClasses 'X2Ability_TLE_Abilities.uc')).Hash
        $backupRoot = Join-Path $fixtureRoot 'junction source backups'
        $refused = $false
        try { & $repair -SdkPath $caseSdk -BackupRoot $backupRoot -Apply | Out-Null } catch { $refused = $true }
        Assert-True $refused 'Repair followed a source-directory junction.'
        Assert-True (!(Test-Path -LiteralPath $backupRoot)) 'Source junction created a backup.'
        Assert-True ((Get-FileHash -LiteralPath (Join-Path $externalClasses 'X2Ability_TLE_Abilities.uc')).Hash -eq $externalHash) 'Source junction changed a file outside the SDK.'

        # A junction in an SDK ancestor can hide a physical BackupRoot inside
        # that same SDK from a merely lexical containment check.
        $caseSdk = New-CaseFixture 'SDK ancestor target'
        $ancestorLink = Join-Path $fixtureRoot 'SDK ancestor alias'
        New-Item -ItemType Junction -Path $ancestorLink -Target (Split-Path -Parent $caseSdk) | Out-Null
        $junctionsToRemove += $ancestorLink
        $aliasSdk = Join-Path $ancestorLink 'SDK with spaces'
        $beforeAlias = Get-Hashes $caseSdk
        $insideBackup = Join-Path $caseSdk 'must not be created'
        $refused = $false
        try { & $repair -SdkPath $aliasSdk -BackupRoot $insideBackup -Apply | Out-Null } catch { $refused = $true }
        Assert-True $refused 'SDK ancestor junction bypassed the outside-SDK backup requirement.'
        Assert-HashesEqual $beforeAlias (Get-Hashes $caseSdk) 'SDK ancestor alias allowed a partial repair'
        Assert-True (!(Test-Path -LiteralPath $insideBackup)) 'SDK ancestor alias created a backup inside the SDK.'
    }

    Write-Host 'PASS: report-only; 22 identical source duplicates and 2 caches backed up with manifest; canonical and unrelated sources preserved; no-op repeat; mismatch, unsafe backup and missing canonical refused before changes.'
}
finally {
    foreach ($junction in $junctionsToRemove) {
        if (Test-Path -LiteralPath $junction) { [IO.Directory]::Delete($junction) }
    }
    if (Test-Path -LiteralPath $fixtureRoot) {
        Remove-Item -LiteralPath $fixtureRoot -Recurse -Force
    }
}
