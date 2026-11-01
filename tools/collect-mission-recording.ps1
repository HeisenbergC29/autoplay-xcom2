#requires -Version 5.1
<#
.SYNOPSIS
Collect WOTC mission logs with the same script shipped in the installed mod.
#>
[CmdletBinding()]
param(
    [string] $LogDirectory,
    [string] $OutputPath,
    [string] $SavePath,
    [ValidateRange(0, 5)][int] $BackupLogs
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$collector = Join-Path (Split-Path -Parent $PSScriptRoot) 'AutoplayXCom2/Diagnostics/Collect-MissionRecording.ps1'
& $collector @PSBoundParameters
