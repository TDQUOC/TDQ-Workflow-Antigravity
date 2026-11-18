# TDQ-Workflow Antigravity User-Level One-Click Installer for Windows
[CmdletBinding()]
param(
    [switch]$DryRun,
    [switch]$NoEnable,
    [switch]$Update,
    [switch]$WithRtk,
    [switch]$SkipRtk,
    [switch]$WithCaveman,
    [switch]$SkipCaveman
)
$params = @()
if ($DryRun) { $params += "--dry-run" }
if ($NoEnable) { $params += "--no-enable" }
if ($Update) { $params += "--update" }
if ($WithRtk) { $params += "--with-rtk" }
if ($SkipRtk) { $params += "--skip-rtk" }
if ($WithCaveman) { $params += "--with-caveman" }
if ($SkipCaveman) { $params += "--skip-caveman" }

if (Get-Command py -ErrorAction SilentlyContinue) {
    py -3 "$PSScriptRoot\install.py" @params
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    python "$PSScriptRoot\install.py" @params
} else {
    Write-Error "Python 3 is required but was not found on PATH."
    exit 1
}
