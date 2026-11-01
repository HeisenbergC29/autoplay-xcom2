#requires -Version 5.1
[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$collector = Join-Path (Split-Path -Parent $PSScriptRoot) 'tools/collect-mission-recording.ps1'
$canonical = Join-Path (Split-Path -Parent $PSScriptRoot) 'AutoplayXCom2/Diagnostics/Collect-MissionRecording.ps1'
$tokens = $null
$errors = $null
[void] [System.Management.Automation.Language.Parser]::ParseFile($collector, [ref] $tokens, [ref] $errors)
if ($errors.Count -gt 0) { throw ($errors.Message -join '; ') }
[void] [System.Management.Automation.Language.Parser]::ParseFile($canonical, [ref] $tokens, [ref] $errors)
if ($errors.Count -gt 0) { throw ($errors.Message -join '; ') }
Add-Type -AssemblyName System.IO.Compression.FileSystem
function Assert-True([bool] $Condition, [string] $Message) {
    if (!$Condition) { throw $Message }
}
$fixture = Join-Path ([IO.Path]::GetTempPath()) ('APX mission collector ' + [Guid]::NewGuid().ToString('N'))
$logs = Join-Path $fixture 'Logs with spaces'
New-Item -ItemType Directory -Path $logs -Force | Out-Null
try {
    $launch = Join-Path $logs 'Launch.log'
    [IO.File]::WriteAllText($launch, 'APXREC|v=1|session=s1|seq=1|event=start')
    [IO.File]::WriteAllText((Join-Path $logs 'Launch-backup-old.log'), 'old backup')
    [IO.File]::WriteAllText((Join-Path $logs 'Launch-backup-new.log'), 'new backup')
    [IO.File]::SetLastWriteTimeUtc((Join-Path $logs 'Launch-backup-old.log'), [DateTime]::UtcNow.AddHours(-2))
    [IO.File]::SetLastWriteTimeUtc((Join-Path $logs 'Launch-backup-new.log'), [DateTime]::UtcNow.AddHours(-1))
    [IO.File]::WriteAllText((Join-Path $logs 'Unrelated.log'), 'must not collect')
    [IO.File]::WriteAllText((Join-Path $logs 'XComGame.uc'), 'must not collect')
    $save = Join-Path $fixture 'TestSave.XComSave'
    [IO.File]::WriteAllText($save, 'explicit save fixture')
    $originalHash = (Get-FileHash -LiteralPath $launch).Hash
    $output = Join-Path $fixture 'Output/report.zip'
    & $collector -LogDirectory $logs -OutputPath $output -BackupLogs 1
    $archive = [IO.Compression.ZipFile]::OpenRead($output)
    try {
        $names = @($archive.Entries | ForEach-Object { $_.FullName.Replace('\', '/') })
        Assert-True ($names.Count -eq 3) 'Unexpected default report payload.'
        foreach ($name in @('Logs/Launch.log', 'Logs/Launch-backup-new.log', 'manifest.json')) {
            Assert-True ($names -contains $name) "Missing report entry $name"
        }
        $reader = [IO.StreamReader]::new($archive.GetEntry('manifest.json').Open())
        try { $manifest = $reader.ReadToEnd() | ConvertFrom-Json } finally { $reader.Dispose() }
        Assert-True ($manifest.files.Count -eq 2) 'Manifest file count incorrect.'
        $entry = @($manifest.files | Where-Object path -eq 'Logs/Launch.log')[0]
        Assert-True ($entry.sha256 -eq $originalHash.ToLowerInvariant()) 'Manifest hash does not match source snapshot.'
        Assert-True ($entry.bytes -eq (Get-Item -LiteralPath $launch).Length) 'Manifest byte count incorrect.'
    }
    finally { $archive.Dispose() }
    Assert-True ((Get-FileHash -LiteralPath $launch).Hash -eq $originalHash) 'Source log modified.'
    $outputHash = (Get-FileHash -LiteralPath $output).Hash
    $refused = $false
    try { & $collector -LogDirectory $logs -OutputPath $output } catch { $refused = $true }
    Assert-True $refused 'Existing report overwritten.'
    Assert-True ((Get-FileHash -LiteralPath $output).Hash -eq $outputHash) 'Existing report bytes changed.'
    $withSave = Join-Path $fixture 'with-save.zip'
    & $canonical -LogDirectory $logs -OutputPath $withSave -BackupLogs 0 -SavePath $save
    $archive = [IO.Compression.ZipFile]::OpenRead($withSave)
    try {
        Assert-True ($null -ne $archive.GetEntry('Save/TestSave.XComSave')) 'Explicitly selected save missing.'
        Assert-True ($archive.Entries.Count -eq 3) 'Optional save payload count incorrect.'
    }
    finally { $archive.Dispose() }
    $missing = Join-Path $fixture 'missing.zip'
    $emptyLogs = Join-Path $fixture 'EmptyLogs'
    New-Item -ItemType Directory -Path $emptyLogs | Out-Null
    $refused = $false
    try { & $collector -LogDirectory $emptyLogs -OutputPath $missing } catch { $refused = $true }
    Assert-True $refused 'Missing Launch.log accepted.'
    Assert-True (!(Test-Path -LiteralPath $missing)) 'Missing logs produced report.'
    $invalidSave = Join-Path $fixture 'invalid-save.zip'
    $refused = $false
    try { & $collector -LogDirectory $logs -OutputPath $invalidSave -SavePath $launch } catch { $refused = $true }
    Assert-True $refused 'Arbitrary non-save file accepted.'
    Assert-True (!(Test-Path -LiteralPath $invalidSave)) 'Invalid save produced report.'
    Write-Host 'PASS: collector parses; log-only snapshot, newest bounded backups, manifest hashes, optional explicit save, source preservation, overwrite refusal and missing-log checks.'
}
finally { Remove-Item -LiteralPath $fixture -Recurse -Force }
