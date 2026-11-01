#requires -Version 5.1
<#
.SYNOPSIS
Copy WOTC logs into a timestamped report ZIP without changing the originals.
.DESCRIPTION
Run after a mission, before starting the game again. The default output is in
Documents/AutoplayXCom2-Reports so it survives deleting downloaded mod sources.
A tactical save is included only when its path is explicitly supplied.
#>
[CmdletBinding()]
param(
    [string] $LogDirectory = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'My Games/XCOM2 War of the Chosen/XComGame/Logs'),
    [string] $OutputPath,
    [string] $SavePath,
    [ValidateRange(0, 5)][int] $BackupLogs = 3
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem
$LogDirectory = (Resolve-Path -LiteralPath $LogDirectory).Path
$launch = Join-Path $LogDirectory 'Launch.log'
if (!(Test-Path -LiteralPath $launch -PathType Leaf)) {
    throw "Launch.log not found in: $LogDirectory"
}
if (!$OutputPath) {
    $reportRoot = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'AutoplayXCom2-Reports'
    $OutputPath = Join-Path $reportRoot ('AutoplayXCom2-{0}-{1}.zip' -f ([DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss')), ([Guid]::NewGuid().ToString('N').Substring(0, 8)))
}
$OutputPath = [IO.Path]::GetFullPath($OutputPath)
if ([IO.Path]::GetExtension($OutputPath) -ine '.zip') { throw 'OutputPath must end with .zip.' }
if (Test-Path -LiteralPath $OutputPath) {
    throw "Output already exists; choose a new path: $OutputPath"
}
if ($SavePath) {
    $SavePath = (Resolve-Path -LiteralPath $SavePath).Path
    if (!(Test-Path -LiteralPath $SavePath -PathType Leaf) -or [IO.Path]::GetExtension($SavePath) -ine '.XComSave') {
        throw 'SavePath must be an explicitly selected .XComSave file.'
    }
}

# FileShare.ReadWrite allows collection while the game still has its log open.
# All manifests hash the actual copied bytes, which may be a partial live log.
function Copy-SharedFile([string] $Source, [string] $Destination) {
    $inputStream = [IO.File]::Open($Source, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::ReadWrite)
    try {
        $outputStream = [IO.File]::Open($Destination, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
        try {
            $remaining = $inputStream.Length
            if ($remaining -gt 128MB) { throw 'Source exceeds 128 MiB.' }
            $buffer = New-Object byte[] 65536
            while ($remaining -gt 0) {
                $read = $inputStream.Read($buffer, 0, [int] [Math]::Min($buffer.Length, $remaining))
                if ($read -eq 0) { break }
                $outputStream.Write($buffer, 0, $read)
                $remaining -= $read
            }
        }
        finally { $outputStream.Dispose() }
    }
    finally { $inputStream.Dispose() }
}

$temporary = Join-Path ([IO.Path]::GetTempPath()) ('apx-mission-' + [Guid]::NewGuid().ToString('N'))
$archiveTemporary = Join-Path ([IO.Path]::GetTempPath()) ('apx-mission-' + [Guid]::NewGuid().ToString('N') + '.zip')
New-Item -ItemType Directory -Path (Join-Path $temporary 'Logs') -Force | Out-Null
try {
    $files = @((Get-Item -LiteralPath $launch))
    if ($BackupLogs -gt 0) {
        $files += @(Get-ChildItem -LiteralPath $LogDirectory -File |
            Where-Object { $_.Name -match '^Launch-backup[^\\/]*\.log$' } |
            Sort-Object LastWriteTimeUtc -Descending | Select-Object -First $BackupLogs)
    }
    $manifestFiles = @()
    $totalBytes = 0
    foreach ($file in $files) {
        if ($file.Length -gt 128MB) { throw "Log too large to collect (limit 128 MiB): $($file.Name)" }
        $relative = 'Logs/' + $file.Name
        $copy = Join-Path $temporary $relative
        Copy-SharedFile $file.FullName $copy
        $totalBytes += (Get-Item -LiteralPath $copy).Length
        if ($totalBytes -gt 256MB) { throw 'Report exceeds 256 MiB. Reduce BackupLogs.' }
        $manifestFiles += [ordered] @{
            path = $relative
            bytes = (Get-Item -LiteralPath $copy).Length
            sha256 = (Get-FileHash -LiteralPath $copy -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    }
    if ($SavePath) {
        if ((Get-Item -LiteralPath $SavePath).Length -gt 128MB) { throw 'Selected save exceeds 128 MiB.' }
        New-Item -ItemType Directory -Path (Join-Path $temporary 'Save') | Out-Null
        $relative = 'Save/' + [IO.Path]::GetFileName($SavePath)
        $copy = Join-Path $temporary $relative
        Copy-SharedFile $SavePath $copy
        $totalBytes += (Get-Item -LiteralPath $copy).Length
        if ($totalBytes -gt 256MB) { throw 'Report exceeds 256 MiB. Reduce BackupLogs or omit SavePath.' }
        $manifestFiles += [ordered] @{
            path = $relative
            bytes = (Get-Item -LiteralPath $copy).Length
            sha256 = (Get-FileHash -LiteralPath $copy -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    }
    $manifest = [ordered] @{
        format_version = 1
        collected_utc = [DateTime]::UtcNow.ToString('o')
        note = 'Copied game logs; a live game may leave the last record incomplete. Saves are opt-in. No SDK files collected.'
        files = $manifestFiles
    }
    $manifestText = $manifest | ConvertTo-Json -Depth 5
    [IO.File]::WriteAllText((Join-Path $temporary 'manifest.json'), $manifestText, [Text.UTF8Encoding]::new($false))
    [IO.Compression.ZipFile]::CreateFromDirectory($temporary, $archiveTemporary)
    $parent = Split-Path -Parent $OutputPath
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
    # Move refuses a concurrent/newly created destination as well.
    [IO.File]::Move($archiveTemporary, $OutputPath)
    Write-Host "Mission report: $OutputPath"
    Write-Host 'Attach this ZIP to the chat. Close the game after the mission before collecting when practical.'
}
finally {
    if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Recurse -Force }
    if (Test-Path -LiteralPath $archiveTemporary) { Remove-Item -LiteralPath $archiveTemporary -Force }
}
