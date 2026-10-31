#requires -Version 5.1
<#
.SYNOPSIS
Check build-directory safety without running the SDK compiler or the build entrypoint.
.DESCRIPTION
Runs on Windows PowerShell 5.1 or PowerShell 7. Uses disposable temporary files.
These checks do not validate compilation, game installation, or in-game behavior.
#>
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$buildScript = Join-Path $repoRoot 'tools/build.ps1'
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    $buildScript, [ref] $tokens, [ref] $parseErrors)
if ($parseErrors.Count -gt 0) {
    throw ('build.ps1 has parser errors: ' + ($parseErrors.Message -join '; '))
}

# Load only the two filesystem helpers; do not execute the Windows-only entrypoint.
$definitions = $ast.FindAll({
    param($node)
    $node -is [System.Management.Automation.Language.FunctionDefinitionAst]
}, $true)
foreach ($helperName in @('Reset-OwnedDirectory', 'Copy-MissingSdkSources')) {
    $definition = @($definitions | Where-Object Name -eq $helperName)
    if ($definition.Count -ne 1) { throw "Expected exactly one $helperName helper." }
    Invoke-Expression $definition[0].Extent.Text
}

# Resolve ownership metadata from literal assignments in the real build script.
foreach ($variableName in @('markerName', 'markerContents')) {
    $assignment = @($ast.FindAll({
        param($node)
        $node -is [System.Management.Automation.Language.AssignmentStatementAst] -and
        $node.Left -is [System.Management.Automation.Language.VariableExpressionAst] -and
        $node.Left.VariablePath.UserPath -eq $variableName
    }, $true))
    if ($assignment.Count -ne 1) { throw "Expected one literal $variableName assignment." }
    if ($assignment[0].Right -isnot [System.Management.Automation.Language.CommandExpressionAst]) {
        throw "Expected a literal expression for $variableName."
    }
    Set-Variable -Name $variableName -Value $assignment[0].Right.Expression.SafeGetValue()
}

function Assert-True([bool] $Condition, [string] $Message) {
    if (!$Condition) { throw $Message }
}

$fixture = Join-Path ([IO.Path]::GetTempPath()) ('APX build helper tests ' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $fixture | Out-Null
try {
    # An unknown directory is never reset, including all its nested files.
    $unknown = Join-Path $fixture 'unknown'
    $unknownChild = Join-Path $unknown 'nested'
    New-Item -ItemType Directory -Path $unknownChild -Force | Out-Null
    $userFile = Join-Path $unknownChild 'user-file.txt'
    [IO.File]::WriteAllText($userFile, 'preserve my work')
    $refused = $false
    try { Reset-OwnedDirectory $unknown } catch { $refused = $true }
    Assert-True $refused 'Unknown directory was accepted for reset.'
    Assert-True ([IO.File]::ReadAllText($userFile) -eq 'preserve my work') 'Unknown directory content changed.'
    Assert-True (!(Test-Path -LiteralPath (Join-Path $unknown $markerName))) 'Unknown directory was marked owned.'

    # A marker from a different owner must not permit removal either.
    $unknownMarker = Join-Path $unknown $markerName
    [IO.File]::WriteAllText($unknownMarker, 'different owner')
    $refused = $false
    try { Reset-OwnedDirectory $unknown } catch { $refused = $true }
    Assert-True $refused 'Wrong ownership marker was accepted.'
    Assert-True ([IO.File]::ReadAllText($userFile) -eq 'preserve my work') 'Wrong-marker refusal changed user content.'

    # Owned outputs can be reset repeatedly, retaining their ownership marker.
    $owned = Join-Path $fixture 'owned'
    Reset-OwnedDirectory $owned
    $stale = Join-Path $owned 'stale-output.txt'
    [IO.File]::WriteAllText($stale, 'stale')
    Reset-OwnedDirectory $owned
    Assert-True (!(Test-Path -LiteralPath $stale)) 'Owned stale output was not removed.'
    Reset-OwnedDirectory $owned
    Assert-True ([IO.File]::ReadAllText((Join-Path $owned $markerName)) -eq $markerContents) 'Ownership marker lost on repeated reset.'

    # SDK initialization copies absent source files, preserving existing edits.
    $srcOrig = Join-Path $fixture 'SrcOrig'
    $srcRoot = Join-Path $fixture 'Src'
    $originalClasses = Join-Path $srcOrig 'XComGame/Classes'
    $preparedClasses = Join-Path $srcRoot 'XComGame/Classes'
    New-Item -ItemType Directory -Path $originalClasses -Force | Out-Null
    New-Item -ItemType Directory -Path $preparedClasses -Force | Out-Null
    $originalExisting = Join-Path $originalClasses 'Existing.uc'
    $preparedExisting = Join-Path $preparedClasses 'Existing.uc'
    $originalMissing = Join-Path $originalClasses 'Missing.uc'
    $preparedMissing = Join-Path $preparedClasses 'Missing.uc'
    [IO.File]::WriteAllText($originalExisting, 'original SDK source')
    [IO.File]::WriteAllText($originalMissing, 'missing source')
    [IO.File]::WriteAllText($preparedExisting, 'local SDK patch')
    [IO.File]::WriteAllText((Join-Path $originalClasses 'DoNotCopy.upk'), 'not script source')
    New-Item -ItemType Directory -Path (Join-Path $srcOrig 'Core') -Force | Out-Null
    [IO.File]::WriteAllText((Join-Path $srcOrig 'Core/Globals.uci'), 'macro source')
    Copy-MissingSdkSources
    Assert-True ([IO.File]::ReadAllText($preparedExisting) -eq 'local SDK patch') 'Existing SDK source was overwritten.'
    Assert-True ([IO.File]::ReadAllText($preparedMissing) -eq 'missing source') 'Missing SDK source was not copied.'
    Assert-True ([IO.File]::ReadAllText((Join-Path $srcRoot 'Core/Globals.uci')) -eq 'macro source') 'Missing SDK macros were not copied.'
    Assert-True (!(Test-Path -LiteralPath (Join-Path $preparedClasses 'DoNotCopy.upk'))) 'Non-source SDK asset was copied.'

    # Repeating setup must preserve edits made after the first initialization too.
    [IO.File]::WriteAllText($preparedMissing, 'patch after first initialization')
    [IO.File]::WriteAllText($originalExisting, 'changed upstream source')
    Copy-MissingSdkSources
    Assert-True ([IO.File]::ReadAllText($preparedExisting) -eq 'local SDK patch') 'Repeated initialization overwrote an existing patch.'
    Assert-True ([IO.File]::ReadAllText($preparedMissing) -eq 'patch after first initialization') 'Repeated initialization replaced a later edit.'

    Write-Host 'PASS: build.ps1 parses; unknown trees preserved; owned reset repeatable; missing SDK sources copied; existing patches preserved on repeat.'
}
finally {
    Remove-Item -LiteralPath $fixture -Recurse -Force
}
