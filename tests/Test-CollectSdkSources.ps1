#requires -Version 5.1
<#
.SYNOPSIS
Exercise SDK collection with disposable source and configuration fixtures.
.DESCRIPTION
Checks source-tree choice, exact selected configuration, archive hashes and
preservation. No SDK, native compiler or game is used.
#>
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$collector = Join-Path $repoRoot 'tools/collect-sdk-sources.ps1'
$tokens = $null
$parseErrors = $null
[void] [System.Management.Automation.Language.Parser]::ParseFile(
    $collector, [ref] $tokens, [ref] $parseErrors)
if ($parseErrors.Count -gt 0) {
    throw ('Collector has parser errors: ' + ($parseErrors.Message -join '; '))
}
Add-Type -AssemblyName System.IO.Compression.FileSystem

function Assert-True([bool] $Condition, [string] $Message) {
    if (!$Condition) { throw $Message }
}

function Assert-ArchiveSources([string] $ArchivePath, [hashtable] $Expected,
    [string] $ExpectedTree, [bool] $ExpectedConfig = $false) {
    $archive = [IO.Compression.ZipFile]::OpenRead($ArchivePath)
    try {
        $fileEntries = @($archive.Entries | Where-Object { $_.Name -ne '' })
        Assert-True ($fileEntries.Count -eq ($Expected.Count + 1)) 'Unexpected ZIP file count.'
        $manifestEntries = @($fileEntries | Where-Object { $_.FullName -eq 'sdk-review-manifest.json' })
        Assert-True ($manifestEntries.Count -eq 1) 'Expected exactly one root manifest.'
        $reader = [IO.StreamReader]::new($manifestEntries[0].Open())
        try { $manifest = $reader.ReadToEnd() | ConvertFrom-Json } finally { $reader.Dispose() }
        $rootProperties = @($manifest.PSObject.Properties.Name)
        Assert-True ($rootProperties.Count -eq 4) 'Manifest exposes unexpected metadata.'
        foreach ($name in @('Version', 'SourceTree', 'BuildConfigIncluded', 'Files')) {
            Assert-True ($rootProperties -contains $name) ('Manifest property missing: ' + $name)
        }
        Assert-True ($manifest.Version -eq 1) 'Unexpected manifest version.'
        Assert-True ($manifest.SourceTree -eq $ExpectedTree) 'Manifest chose the wrong source tree.'
        Assert-True ($manifest.BuildConfigIncluded -eq $ExpectedConfig) 'Manifest configuration mode is wrong.'
        $manifestFiles = @($manifest.Files)
        Assert-True ($manifestFiles.Count -eq $Expected.Count) 'Manifest file count differs from contents.'
        $byPath = @{}
        foreach ($file in $manifestFiles) {
            $relative = [string] $file.Path
            Assert-True (!$relative.StartsWith('/') -and $relative -notmatch '(^|/)\.\.(/|$)|:|\\') 'Manifest contains an absolute or escaping path.'
            Assert-True ($Expected.ContainsKey($relative)) ('Unexpected manifest path: ' + $relative)
            Assert-True (!$byPath.ContainsKey($relative)) ('Duplicate manifest path: ' + $relative)
            Assert-True (@($file.PSObject.Properties.Name).Count -eq 3) 'Manifest file has unexpected metadata.'
            $byPath[$relative] = $file
        }
        foreach ($entry in $fileEntries) {
            $relative = $entry.FullName.Replace('\', '/')
            Assert-True (!$relative.StartsWith('/') -and $relative -notmatch '(^|/)\.\.(/|$)|:') 'Archive contains an absolute or escaping path.'
            if ($relative -eq 'sdk-review-manifest.json') { continue }
            Assert-True ($Expected.ContainsKey($relative)) ('Unexpected archive entry: ' + $relative)
            Assert-True ($byPath.ContainsKey($relative)) ('Missing manifest entry: ' + $relative)
            $sha = [Security.Cryptography.SHA256]::Create()
            $stream = $entry.Open()
            try { $actualHash = [BitConverter]::ToString($sha.ComputeHash($stream)).Replace('-', '') }
            finally { $stream.Dispose(); $sha.Dispose() }
            Assert-True ($byPath[$relative].SHA256 -ceq $actualHash) ('Wrong archive hash: ' + $relative)
            Assert-True ([long] $byPath[$relative].Bytes -eq $entry.Length) ('Wrong byte count: ' + $relative)
            $reader = [IO.StreamReader]::new($entry.Open())
            try { $contents = $reader.ReadToEnd() } finally { $reader.Dispose() }
            Assert-True ($contents -eq $Expected[$relative]) ('Archived content changed: ' + $relative)
        }
    }
    finally { $archive.Dispose() }
}

$fixture = Join-Path ([IO.Path]::GetTempPath()) ('APX SDK source tests ' + [guid]::NewGuid().ToString('N'))
$sdk = Join-Path $fixture 'SDK with spaces'
$srcOrig = Join-Path $sdk 'Development/SrcOrig'
$src = Join-Path $sdk 'Development/Src'
$config = Join-Path $sdk 'XComGame/Config'
foreach ($path in @((Join-Path $srcOrig 'XComGame/Classes'), (Join-Path $srcOrig 'Core'),
                    (Join-Path $src 'XComGame/Classes'), $config)) {
    New-Item -ItemType Directory -Path $path -Force | Out-Null
}
try {
    $origText = 'class Test extends Object; // original tree'
    $srcText = 'class Fallback extends Object; // compiled working tree'
    $globalsText = '`define APX_TEST true'
    $defaultConfig = '[UnrealEd.EditorEngine]' + [Environment]::NewLine + '+EditPackages=XCom_DLC_Day0'
    $generatedConfig = '[UnrealEd.EditorEngine]' + [Environment]::NewLine + 'EditPackages=XComGame'
    [IO.File]::WriteAllText((Join-Path $srcOrig 'XComGame/Classes/Test.uc'), $origText)
    [IO.File]::WriteAllText((Join-Path $srcOrig 'Core/Globals.uci'), $globalsText)
    [IO.File]::WriteAllText((Join-Path $src 'XComGame/Classes/Fallback.uc'), $srcText)
    [IO.File]::WriteAllBytes((Join-Path $srcOrig 'decoy.bin'), [byte[]] @(0, 1, 2, 255))
    [IO.File]::WriteAllBytes((Join-Path $src 'decoy.u'), [byte[]] @(4, 5, 6))
    [IO.File]::WriteAllText((Join-Path $config 'DefaultEngine.ini'), $defaultConfig)
    [IO.File]::WriteAllText((Join-Path $config 'XComEngine.ini'), $generatedConfig)
    [IO.File]::WriteAllText((Join-Path $config 'UnrelatedPrivate.ini'), 'must not be collected')

    $output = Join-Path $fixture 'sdk review.zip'
    & $collector -SdkPath $sdk -OutputPath $output
    Assert-ArchiveSources $output @{
        'XComGame/Classes/Test.uc' = $origText
        'Core/Globals.uci' = $globalsText
    } 'SrcOrig'

    # Explicit Src must select the actual working tree even when SrcOrig is valid.
    $workingOutput = Join-Path $fixture 'working source.zip'
    & $collector -SdkPath $sdk -SourceTree Src -OutputPath $workingOutput
    Assert-ArchiveSources $workingOutput @{
        'XComGame/Classes/Fallback.uc' = $srcText
    } 'Src'

    $configuredOutput = Join-Path $fixture 'working source and config.zip'
    & $collector -SdkPath $sdk -SourceTree Src -IncludeBuildConfig -OutputPath $configuredOutput
    Assert-ArchiveSources $configuredOutput @{
        'XComGame/Classes/Fallback.uc' = $srcText
        'SDKBuildConfig/DefaultEngine.ini' = $defaultConfig
        'SDKBuildConfig/XComEngine.ini' = $generatedConfig
    } 'Src' $true

    # Existing archives are refused, rather than replaced with a newer snapshot.
    $originalHash = (Get-FileHash -LiteralPath $output -Algorithm SHA256).Hash
    [IO.File]::WriteAllText((Join-Path $srcOrig 'XComGame/Classes/Test.uc'), 'changed source')
    $refused = $false
    try { & $collector -SdkPath $sdk -OutputPath $output } catch { $refused = $true }
    Assert-True $refused 'Collector accepted an existing output archive.'
    Assert-True ((Get-FileHash -LiteralPath $output -Algorithm SHA256).Hash -eq $originalHash) 'Existing archive was modified.'

    # Both selected INIs are required; one missing INI must not produce a partial ZIP.
    Remove-Item -LiteralPath (Join-Path $config 'XComEngine.ini')
    $missingConfigOutput = Join-Path $fixture 'missing config.zip'
    $refused = $false
    try { & $collector -SdkPath $sdk -SourceTree Src -IncludeBuildConfig -OutputPath $missingConfigOutput } catch { $refused = $true }
    Assert-True $refused 'Collector accepted an incomplete configuration snapshot.'
    Assert-True (!(Test-Path -LiteralPath $missingConfigOutput)) 'Missing config produced a ZIP.'

    foreach ($requested in @('Src', 'SrcOrig')) {
        $alternate = 'Src'
        if ($requested -eq 'Src') { $alternate = 'SrcOrig' }
        $oneTreeSdk = Join-Path $fixture ('Only ' + $alternate)
        $classes = Join-Path $oneTreeSdk ('Development/' + $alternate + '/XComGame/Classes')
        New-Item -ItemType Directory -Path $classes -Force | Out-Null
        [IO.File]::WriteAllText((Join-Path $classes 'Test.uc'), 'class Test extends Object;')
        $missingTreeOutput = Join-Path $fixture ('missing ' + $requested + '.zip')
        $refused = $false
        try { & $collector -SdkPath $oneTreeSdk -SourceTree $requested -OutputPath $missingTreeOutput } catch { $refused = $true }
        Assert-True $refused ('Explicit missing tree silently fell back: ' + $requested)
        Assert-True (!(Test-Path -LiteralPath $missingTreeOutput)) 'Missing explicit tree produced a ZIP.'
    }

    # Auto retains the old fallback when SrcOrig exists but is incomplete.
    Remove-Item -LiteralPath (Join-Path $srcOrig 'XComGame') -Recurse -Force
    $fallbackOutput = Join-Path $fixture 'sdk fallback.zip'
    & $collector -SdkPath $sdk -OutputPath $fallbackOutput
    Assert-ArchiveSources $fallbackOutput @{
        'XComGame/Classes/Fallback.uc' = $srcText
    } 'Src'

    $missingSdk = Join-Path $fixture 'Missing SDK'
    New-Item -ItemType Directory -Path $missingSdk -Force | Out-Null
    $missingOutput = Join-Path $fixture 'must not exist.zip'
    $refused = $false
    try { & $collector -SdkPath $missingSdk -OutputPath $missingOutput } catch { $refused = $true }
    Assert-True $refused 'Missing SDK sources were accepted.'
    Assert-True (!(Test-Path -LiteralPath $missingOutput)) 'Missing sources produced an archive.'
    Write-Host 'PASS: source-tree choice and legacy fallback; selected config only; ZIP bytes/hash manifest; relative paths; no clobber or partial snapshots.'
}
finally {
    Remove-Item -LiteralPath $fixture -Recurse -Force
}
