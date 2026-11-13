#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $SdkPath,
    [string] $OutputPath = (Join-Path (Split-Path -Parent $PSScriptRoot) 'sdk-for-review.zip'),
    [ValidateSet('Auto', 'Src', 'SrcOrig')][string] $SourceTree = 'Auto',
    [switch] $IncludeBuildConfig
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$SdkPath = (Resolve-Path -LiteralPath $SdkPath).Path
$source = $null
$selectedTree = $null
$candidateTrees = @('SrcOrig', 'Src')
if ($SourceTree -eq 'Src') { $candidateTrees = @('Src') }
elseif ($SourceTree -eq 'SrcOrig') { $candidateTrees = @('SrcOrig') }
foreach ($tree in $candidateTrees) {
    $candidate = Join-Path $SdkPath ('Development/' + $tree)
    if (Test-Path -LiteralPath (Join-Path $candidate 'XComGame\Classes') -PathType Container) {
        $source = $candidate
        $selectedTree = $tree
        break
    }
}
if (!$source) {
    if ($SourceTree -ne 'Auto') {
        throw "Selected SDK source tree is missing: Development/$SourceTree/XComGame/Classes. No alternate tree was collected."
    }
    throw 'SDK sources missing: expected Development\SrcOrig\XComGame\Classes or Development\Src\XComGame\Classes.'
}
if (Test-Path -LiteralPath $OutputPath) {
    throw "Output already exists; preserve or remove it explicitly before retrying: $OutputPath"
}
$configFiles = @('DefaultEngine.ini', 'XComEngine.ini')
if ($IncludeBuildConfig) {
    foreach ($name in $configFiles) {
        $path = Join-Path $SdkPath ('XComGame/Config/' + $name)
        if (!(Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Requested SDK build configuration is missing: XComGame/Config/$name. No archive created."
        }
    }
}
$temporary = Join-Path ([IO.Path]::GetTempPath()) ('apx-sdk-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $temporary | Out-Null
try {
    $count = 0
    $manifestFiles = @()
    foreach ($file in Get-ChildItem -LiteralPath $source -Recurse -File) {
        if ($file.Extension -notin @('.uc', '.uci')) { continue }
        $relative = $file.FullName.Substring($source.Length).TrimStart('\', '/')
        $target = Join-Path $temporary $relative
        New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
        Copy-Item -LiteralPath $file.FullName -Destination $target
        # Hash the staged bytes that actually enter the archive, not a later
        # revision of an SDK source file which may change during collection.
        $manifestFiles += [pscustomobject] @{
            Path = $relative.Replace('\', '/')
            Bytes = (Get-Item -LiteralPath $target).Length
            SHA256 = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
        }
        ++$count
    }
    if ($count -eq 0) { throw 'No UnrealScript source files found.' }
    if ($IncludeBuildConfig) {
        foreach ($name in $configFiles) {
            $relative = 'SDKBuildConfig/' + $name
            $target = Join-Path $temporary $relative
            New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
            Copy-Item -LiteralPath (Join-Path $SdkPath ('XComGame/Config/' + $name)) -Destination $target
            $manifestFiles += [pscustomobject] @{
                Path = $relative
                Bytes = (Get-Item -LiteralPath $target).Length
                SHA256 = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
            }
        }
    }
    $manifest = [ordered] @{
        Version = 1
        SourceTree = $selectedTree
        BuildConfigIncluded = [bool] $IncludeBuildConfig
        Files = @($manifestFiles | Sort-Object Path)
    }
    [IO.File]::WriteAllText((Join-Path $temporary 'sdk-review-manifest.json'),
        ($manifest | ConvertTo-Json -Depth 5), [Text.UTF8Encoding]::new($false))
    Compress-Archive -Path (Join-Path $temporary '*') -DestinationPath $OutputPath
    Write-Host ('Collected {0} source files from Development/{1}: {2}' -f $count, $selectedTree, $OutputPath)
    if ($IncludeBuildConfig) { Write-Host 'Included only SDK DefaultEngine.ini and XComEngine.ini.' }
    Write-Host 'Attach this ZIP to the chat. Do not commit proprietary SDK sources to GitHub.'
}
finally {
    Remove-Item -LiteralPath $temporary -Recurse -Force
}
