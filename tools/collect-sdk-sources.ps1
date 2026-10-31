#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string] $SdkPath,
    [string] $OutputPath = (Join-Path (Split-Path -Parent $PSScriptRoot) 'sdk-for-review.zip')
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$SdkPath = (Resolve-Path -LiteralPath $SdkPath).Path
$source = $null
foreach ($candidate in @((Join-Path $SdkPath 'Development\SrcOrig'), (Join-Path $SdkPath 'Development\Src'))) {
    if (Test-Path -LiteralPath (Join-Path $candidate 'XComGame\Classes') -PathType Container) {
        $source = $candidate
        break
    }
}
if (!$source) {
    throw 'SDK sources missing: expected Development\SrcOrig\XComGame\Classes or Development\Src\XComGame\Classes.'
}
if (Test-Path -LiteralPath $OutputPath) {
    throw "Output already exists; preserve or remove it explicitly before retrying: $OutputPath"
}
$temporary = Join-Path ([IO.Path]::GetTempPath()) ('apx-sdk-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $temporary | Out-Null
try {
    $count = 0
    foreach ($file in Get-ChildItem -LiteralPath $source -Recurse -File) {
        if ($file.Extension -notin @('.uc', '.uci')) { continue }
        $relative = $file.FullName.Substring($source.Length).TrimStart('\', '/')
        $target = Join-Path $temporary $relative
        New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
        Copy-Item -LiteralPath $file.FullName -Destination $target
        ++$count
    }
    if ($count -eq 0) { throw 'No UnrealScript source files found.' }
    Compress-Archive -Path (Join-Path $temporary '*') -DestinationPath $OutputPath
    Write-Host "Collected $count source files: $OutputPath"
    Write-Host 'Attach this ZIP to the chat. Do not commit proprietary SDK sources to GitHub.'
}
finally {
    Remove-Item -LiteralPath $temporary -Recurse -Force
}
