#requires -Version 5.1
<#
.SYNOPSIS
Exercise SDK-source collection with disposable source fixtures; requires no game or SDK.
.DESCRIPTION
Checks source-only ZIP paths, SrcOrig preference, Src fallback, and archive preservation.
This does not validate SDK compilation or mod behavior in the game.
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

function Assert-ArchiveSources([string] $ArchivePath, [hashtable] $Expected) {
    $archive = [IO.Compression.ZipFile]::OpenRead($ArchivePath)
    try {
        $fileEntries = @($archive.Entries | Where-Object { $_.Name -ne '' })
        Assert-True ($fileEntries.Count -eq $Expected.Count) 'Unexpected ZIP file count.'
        foreach ($entry in $archive.Entries) {
            $relative = $entry.FullName.Replace('\', '/')
            Assert-True (!$relative.StartsWith('/') -and $relative -notmatch '(^|/)\.\.(/|$)|:') 'Archive contains an absolute or escaping path.'
            if ($entry.Name -eq '') { continue }
            Assert-True ($Expected.ContainsKey($relative)) "Unexpected archive entry: $relative"
            Assert-True ([IO.Path]::GetExtension($entry.Name) -in @('.uc', '.uci')) 'Archive includes a non-source file.'
            $reader = [IO.StreamReader]::new($entry.Open())
            try { $contents = $reader.ReadToEnd() } finally { $reader.Dispose() }
            Assert-True ($contents -eq $Expected[$relative]) "Archived source changed: $relative"
        }
    }
    finally { $archive.Dispose() }
}

$fixture = Join-Path ([IO.Path]::GetTempPath()) ('APX SDK source tests ' + [guid]::NewGuid().ToString('N'))
$sdk = Join-Path $fixture 'SDK with spaces'
$srcOrig = Join-Path $sdk 'Development/SrcOrig'
$src = Join-Path $sdk 'Development/Src'
New-Item -ItemType Directory -Path (Join-Path $srcOrig 'XComGame/Classes') -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $srcOrig 'Core') -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $src 'XComGame/Classes') -Force | Out-Null
try {
    [IO.File]::WriteAllText((Join-Path $srcOrig 'XComGame/Classes/Test.uc'), 'class Test extends Object;')
    [IO.File]::WriteAllText((Join-Path $srcOrig 'Core/Globals.uci'), '`define APX_TEST true')
    [IO.File]::WriteAllBytes((Join-Path $srcOrig 'decoy.bin'), [byte[]] @(0, 1, 2, 255))
    [IO.File]::WriteAllText((Join-Path $src 'XComGame/Classes/Fallback.uc'), 'class Fallback extends Object;')
    $output = Join-Path $fixture 'sdk review.zip'
    & $collector -SdkPath $sdk -OutputPath $output
    Assert-ArchiveSources $output @{
        'XComGame/Classes/Test.uc' = 'class Test extends Object;'
        'Core/Globals.uci' = '`define APX_TEST true'
    }

    # A second request must refuse to replace the first archive, byte for byte.
    $originalHash = (Get-FileHash -LiteralPath $output -Algorithm SHA256).Hash
    [IO.File]::WriteAllText((Join-Path $srcOrig 'XComGame/Classes/Test.uc'), 'changed source')
    $refused = $false
    try { & $collector -SdkPath $sdk -OutputPath $output } catch { $refused = $true }
    Assert-True $refused 'Collector accepted an existing output archive.'
    Assert-True ((Get-FileHash -LiteralPath $output -Algorithm SHA256).Hash -eq $originalHash) 'Existing archive was modified.'

    # Prefer the valid alternate source tree if SrcOrig exists but is incomplete.
    Remove-Item -LiteralPath (Join-Path $srcOrig 'XComGame') -Recurse -Force
    $fallbackOutput = Join-Path $fixture 'sdk fallback.zip'
    & $collector -SdkPath $sdk -OutputPath $fallbackOutput
    Assert-ArchiveSources $fallbackOutput @{
        'XComGame/Classes/Fallback.uc' = 'class Fallback extends Object;'
    }

    # A missing source installation must fail without producing a ZIP.
    $missingSdk = Join-Path $fixture 'Missing SDK'
    New-Item -ItemType Directory -Path $missingSdk -Force | Out-Null
    $missingOutput = Join-Path $fixture 'must not exist.zip'
    $refused = $false
    try { & $collector -SdkPath $missingSdk -OutputPath $missingOutput } catch { $refused = $true }
    Assert-True $refused 'Missing SDK sources were accepted.'
    Assert-True (!(Test-Path -LiteralPath $missingOutput)) 'Missing sources produced an archive.'
    Write-Host 'PASS: collector parses; ZIP contains source-only relative paths; SrcOrig preferred; Src fallback works; existing archive preserved; missing sources refused.'
}
finally {
    Remove-Item -LiteralPath $fixture -Recurse -Force
}
