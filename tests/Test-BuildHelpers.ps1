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

# Load only testable helpers; do not execute the Windows-only entrypoint.
$definitions = $ast.FindAll({
    param($node)
    $node -is [System.Management.Automation.Language.FunctionDefinitionAst]
}, $true)
foreach ($helperName in @('Reset-OwnedDirectory', 'Copy-MissingSdkSources', 'Convert-LocalizationForGame', 'Copy-ModPayload', 'Assert-SdkCompilerResult')) {
    $definition = @($definitions | Where-Object Name -eq $helperName)
    if ($definition.Count -ne 1) { throw "Expected exactly one $helperName helper." }
    Invoke-Expression $definition[0].Extent.Text
}

# Resolve ownership metadata from literal assignments in the real build script.
foreach ($variableName in @('markerName', 'markerContents', 'modName')) {
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
    # Validate synthetic runner output without executing or faking a compiler.
    # The game SDK's asset warnings are allowed; rejected config defaults in
    # this mod are not, even when the native summary reports zero errors.
    $sdkWarnings = (0..7 | ForEach-Object {
        "C:\SDK\Development\Src\DLC_2\Classes\Fixture$_.uc(1) : Warning, Unresolved reference to StaticMesh 'Fixture.Asset$_'"
    }) -join [Environment]::NewLine
    $resultCases = @(
        @{
            Name = 'zero errors and eight SDK asset warnings'
            ExitCode = 0
            Log = $sdkWarnings + "`nSuccess - 0 error(s), 8 warning(s) (0 Unique Errors, 8 Unique Warnings)"
            Allowed = $true
        },
        @{
            Name = 'own config assignment rejection despite zero errors'
            ExitCode = 0
            Log = "C:\SDK\Development\Src\AutoplayXCom2\Classes\Fixture.uc(9) : Warning, Import failed for 'AttackAbilities': property is config (fixture)`nSuccess - 0 error(s), 1 warning(s)"
            Allowed = $false
        },
        @{
            Name = 'own config assignment rejection with forward slashes'
            ExitCode = 0
            Log = "AutoplayXCom2/Classes/Fixture.uc(9) : Warning, Import failed for 'ToggleKey': property is config`nSuccess - 0 error(s), 1 warning(s)"
            Allowed = $false
        },
        @{
            Name = 'nonzero exit code with no error text'
            ExitCode = 7
            Log = 'Compiler process ended.'
            Allowed = $false
        },
        @{
            Name = 'compiler error despite zero exit code'
            ExitCode = 0
            Log = "C:\SDK\Development\Src\AutoplayXCom2\Classes\Fixture.uc(1) : Error, Fixture error`nFailure - 1 error(s), 0 warning(s)"
            Allowed = $false
        },
        @{
            Name = 'crash despite zero exit code'
            ExitCode = 0
            Log = 'Crash Detected'
            Allowed = $false
        }
    )
    foreach ($resultCase in $resultCases) {
        $accepted = $true
        try { Assert-SdkCompilerResult -LogText $resultCase.Log -ExitCode $resultCase.ExitCode }
        catch { $accepted = $false }
        Assert-True ($accepted -eq $resultCase.Allowed) ("Unexpected compiler-result decision: " + $resultCase.Name)
    }

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

    # Real localized text must survive the exact packaging conversion, including
    # on Windows PowerShell 5.1 whose script-source decoding differs from PS7.
    $localization = Join-Path $fixture 'Localization'
    New-Item -ItemType Directory -Path $localization | Out-Null
    $localizedFile = Join-Path $localization 'AutoplayXCom2.pol'
    $polishText = [string]::Concat('W', [char]0x0141, [char]0x0104, 'CZ AUTOPLAY')
    [IO.File]::WriteAllText($localizedFile, $polishText, [Text.UTF8Encoding]::new($false))
    Convert-LocalizationForGame $localization
    $convertedBytes = [IO.File]::ReadAllBytes($localizedFile)
    Assert-True ($convertedBytes.Length -gt 2 -and $convertedBytes[0] -eq 0xFF -and $convertedBytes[1] -eq 0xFE) 'Localization is missing a UTF-16LE BOM.'
    Assert-True ([IO.File]::ReadAllText($localizedFile) -ceq $polishText) 'Polish characters changed during localization conversion.'
    Convert-LocalizationForGame $localization
    Assert-True ([Convert]::ToBase64String([IO.File]::ReadAllBytes($localizedFile)) -ceq [Convert]::ToBase64String($convertedBytes)) 'Repeated localization conversion changed bytes.'
    Convert-LocalizationForGame (Join-Path $fixture 'MissingLocalization')

    # Packaging must include the actual installation document and omit script
    # sources from the distributable. The fixture bytes below test file copying,
    # not a compiler or a valid game package.
    $payloadSource = Join-Path $fixture 'PayloadSource'
    $payloadStage = Join-Path $fixture 'PayloadStage'
    $payloadOutput = Join-Path $fixture 'PayloadOutput'
    foreach ($directory in @('Config', 'Localization', 'Src', 'Script')) {
        New-Item -ItemType Directory -Path (Join-Path $payloadSource $directory) -Force | Out-Null
    }
    New-Item -ItemType Directory -Path $payloadStage, $payloadOutput | Out-Null
    $realInstructions = Join-Path $repoRoot 'AutoplayXCom2/INSTALL.pl.md'
    Copy-Item -LiteralPath $realInstructions -Destination (Join-Path $payloadSource 'INSTALL.pl.md')
    [IO.File]::WriteAllText((Join-Path $payloadSource "$modName.XComMod"), '[mod]')
    [IO.File]::WriteAllText((Join-Path $payloadSource 'Src/SourceOnly.uc'), 'fixture source')
    [IO.File]::WriteAllText((Join-Path $payloadSource 'Script/Fixture.u'), 'copy-test fixture, not bytecode')
    Copy-ModPayload $payloadSource $payloadStage -IncludeSource
    Assert-True (Test-Path -LiteralPath (Join-Path $payloadStage 'Src/SourceOnly.uc')) 'Staging omitted mod sources.'
    Assert-True (!(Test-Path -LiteralPath (Join-Path $payloadStage 'Script'))) 'Source staging copied an existing script package.'
    Copy-ModPayload $payloadSource $payloadOutput
    Assert-True (Test-Path -LiteralPath (Join-Path $payloadOutput 'Script/Fixture.u')) 'Distribution omitted script directory.'
    Assert-True (!(Test-Path -LiteralPath (Join-Path $payloadOutput 'Src'))) 'Distribution unexpectedly contains script sources.'
    Assert-True ((Get-FileHash -LiteralPath (Join-Path $payloadOutput 'INSTALL.pl.md')).Hash -eq (Get-FileHash -LiteralPath $realInstructions).Hash) 'Installation instructions changed during packaging.'
    Remove-Item -LiteralPath (Join-Path $payloadSource 'INSTALL.pl.md')
    $refused = $false
    try { Copy-ModPayload $payloadSource $payloadOutput } catch { $refused = $true }
    Assert-True $refused 'Packaging accepted a missing installation document.'

    Write-Host 'PASS: build.ps1 parses; compiler failures and rejected own config blocked; SDK asset warnings allowed; unknown trees and SDK patches preserved; Polish UTF-16LE repeatable; correct distribution payload.'
}
finally {
    Remove-Item -LiteralPath $fixture -Recurse -Force
}
