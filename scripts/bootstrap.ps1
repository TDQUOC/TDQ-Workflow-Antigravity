<#
.SYNOPSIS
Zero-to-Full Gate-0 user-space bootstrapper for TDQ-Workflow on Windows Antigravity.
.DESCRIPTION
Prepends %USERPROFILE%\.local\bin ahead of WindowsApps in User PATH, installs missing
user-space runtime dependencies (Git, fnm + Node LTS >= 18, uv + Python 3, agy CLI),
clones/updates tdq-workflow-agy if run outside a checkout, installs the Antigravity
plugin, and triggers tdq_setup.py --setupfully without Administrator elevation.
#>
[CmdletBinding()]
param(
    [switch]$DryRun,
    [string]$StateDir = "",
    [switch]$KhongChamMay,
    [string]$RepoUrl = "https://github.com/TDQUOC/TDQ-Workflow-Antigravity.git",
    [string]$Branch = "dev",
    [string]$PluginBranch = "release/antigravity",
    [switch]$Yes,
    [switch]$Help
)

$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

function Test-AllowedRepoUrl {
    param([string]$Url)
    if ([string]::IsNullOrWhiteSpace($Url) -or $Url.StartsWith("-")) { return $false }
    return ($Url -match '^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?$')
}

function Invoke-VerifiedRemoteScript {
    param([string]$Uri, [string]$Label)
    if (-not ($Uri -match '^https://[A-Za-z0-9.-]+/')) {
        throw "Refusing non-HTTPS installer URL for ${Label}: $Uri"
    }
    $approved = $Yes -or ($env:TDQ_BOOTSTRAP_APPROVE -eq "1")
    if (-not $approved -and [Environment]::UserInteractive -and -not [Console]::IsInputRedirected) {
        $ans = Read-Host "Install $Label from $Uri? [y/N]"
        $approved = ($ans -match '^(?i)(y|yes)$')
    }
    if (-not $approved) {
        Write-TdqLog "Remote installer skipped for $Label without -Yes consent. Official URL: $Uri"
        return $false
    }
    $tmpScript = Join-Path ([System.IO.Path]::GetTempPath()) ("tdq-bs-" + [Guid]::NewGuid().ToString("N") + ".ps1")
    try {
        $resp = Invoke-WebRequest -Uri $Uri -UseBasicParsing -MaximumRedirection 5 -TimeoutSec 30
        if ($resp.StatusCode -lt 200 -or $resp.StatusCode -ge 300) { throw "HTTP status $($resp.StatusCode)" }
        $body = [string]$resp.Content
        if ([string]::IsNullOrWhiteSpace($body) -or $body.TrimStart() -match '^(?i)<(?:!doctype|html)\b') {
            throw "Unexpected HTML or empty response from $Uri"
        }
        [System.IO.File]::WriteAllText($tmpScript, $body, [System.Text.Encoding]::UTF8)
        & $tmpScript
        return $true
    } finally {
        if (Test-Path -LiteralPath $tmpScript) { Remove-Item -LiteralPath $tmpScript -Force -ErrorAction SilentlyContinue }
    }
}

function Write-TdqLog {
    param([string]$Message)
    if ($env:TDQ_LOG -eq "0") { return }
    $stamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss")
    [Console]::Error.WriteLine("[$stamp] bootstrap.ps1: $Message")
}

function Test-DryMode {
    return ($DryRun -or $KhongChamMay -or ($env:TDQ_KHONG_CHAM_MAY -eq "1"))
}

function Test-WindowsAppsStub {
    param([string]$CandidatePath)
    if ([string]::IsNullOrWhiteSpace($CandidatePath)) { return $false }
    return ($CandidatePath.ToLowerInvariant().Contains("windowsapps"))
}

function Resolve-NonStubExe {
    param([string[]]$Names)
    foreach ($name in $Names) {
        $cmds = Get-Command -Name $name -CommandType Application -All -ErrorAction SilentlyContinue
        foreach ($cmd in $cmds) {
            if (-not (Test-WindowsAppsStub $cmd.Source)) {
                return $cmd.Source
            }
        }
    }
    return $null
}

function Build-OrderedPath {
    param(
        [string]$CurrentPath,
        [string[]]$PrependDirs
    )
    $seen = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)
    $ordered = New-Object 'System.Collections.Generic.List[string]'
    foreach ($dir in $PrependDirs) {
        if ([string]::IsNullOrWhiteSpace($dir)) { continue }
        $norm = $dir.Trim().Trim('"').TrimEnd('\')
        if ($norm -and $seen.Add($norm)) {
            $ordered.Add($norm)
        }
    }
    foreach ($entry in ($CurrentPath -split ';')) {
        if ([string]::IsNullOrWhiteSpace($entry)) { continue }
        $norm = $entry.Trim().Trim('"').TrimEnd('\')
        if ($norm -and $seen.Add($norm)) {
            $ordered.Add($norm)
        }
    }
    return ($ordered -join ';')
}

function Ensure-UserPathFront {
    param([string[]]$PrependDirs)
    $env:PATH = Build-OrderedPath -CurrentPath $env:PATH -PrependDirs $PrependDirs
    if (Test-DryMode) {
        Write-TdqLog "[dry-run] Would prepend $($PrependDirs -join ';') ahead of WindowsApps in User PATH"
        return
    }
    foreach ($dir in $PrependDirs) {
        if (-not [string]::IsNullOrWhiteSpace($dir) -and -not (Test-Path -LiteralPath $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }
    }
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($null -eq $userPath) { $userPath = "" }
    $nextPath = Build-OrderedPath -CurrentPath $userPath -PrependDirs $PrependDirs
    if ($nextPath -ne $userPath) {
        [Environment]::SetEnvironmentVariable("Path", $nextPath, "User")
        Write-TdqLog "Updated User PATH ahead of WindowsApps"
    }
}

function Install-WingetUserPackage {
    param(
        [string]$PackageId,
        [string]$Label
    )
    $winget = Resolve-NonStubExe @("winget.exe", "winget")
    if (-not $winget) {
        Write-TdqLog "winget not found; install $Label ($PackageId) manually"
        return $false
    }
    if (Test-DryMode) {
        Write-TdqLog "[dry-run] Would run winget install --id $PackageId --scope user"
        return $true
    }
    Write-TdqLog "Installing $Label via winget ($PackageId)..."
    & "$winget" install --id $PackageId --exact --silent --accept-package-agreements --accept-source-agreements --scope user | Out-Null
    if ($LASTEXITCODE -ne 0) {
        & "$winget" install --id $PackageId --exact --silent --accept-package-agreements --accept-source-agreements | Out-Null
    }
    return ($LASTEXITCODE -eq 0)
}

function Ensure-Git {
    $gitExe = Resolve-NonStubExe @("git.exe", "git")
    if ($gitExe) { return $gitExe }
    $localGit = Join-Path $env:LOCALAPPDATA "Programs\Git\cmd"
    $progGit = Join-Path $env:ProgramFiles "Git\cmd"
    if (-not (Install-WingetUserPackage -PackageId "Git.Git" -Label "Git")) {
        Write-TdqLog "Warning: Git could not be installed automatically. Install Git for Windows from https://git-scm.com/download/win"
        return $null
    }
    Ensure-UserPathFront @($localGit, $progGit)
    return (Resolve-NonStubExe @("git.exe", "git"))
}

function Ensure-FnmAndNode {
    param([string]$LocalBin)
    $nodeExe = Resolve-NonStubExe @("node.exe", "node")
    if ($nodeExe) {
        $verText = & "$nodeExe" --version 2>$null
        if ($verText -match '^v(\d+)\.') {
            if ([int]$Matches[1] -ge 18) { return $nodeExe }
        }
    }
    if (Test-DryMode) {
        Write-TdqLog "[dry-run] Would install fnm + Node.js LTS (>=18) in user-space"
        return $nodeExe
    }
    $fnmExe = Resolve-NonStubExe @("fnm.exe", "fnm")
    if (-not $fnmExe) {
        $ok = Install-WingetUserPackage -PackageId "Schniz.fnm" -Label "fnm"
        if (-not $ok) {
            Write-TdqLog "Attempting user-space fnm install script..."
            [void](Invoke-VerifiedRemoteScript -Uri "https://fnm.vercel.app/install.ps1" -Label "fnm")
        }
        $fnmExe = Resolve-NonStubExe @("fnm.exe", "fnm")
    }
    if ($fnmExe) {
        & "$fnmExe" install --lts | Out-Null
        & "$fnmExe" default lts-latest | Out-Null
        $fnmAlias = Join-Path $env:APPDATA "fnm\aliases\default"
        if (Test-Path -LiteralPath $fnmAlias) {
            Ensure-UserPathFront @($LocalBin, $fnmAlias)
        }
    }
    return (Resolve-NonStubExe @("node.exe", "node"))
}

function Ensure-UvAndPython {
    param([string]$LocalBin)
    $uvExe = Resolve-NonStubExe @("uv.exe", "uv")
    if (-not $uvExe) {
        if (Test-DryMode) {
            Write-TdqLog "[dry-run] Would install uv from https://astral.sh/uv/install.ps1 into $LocalBin"
        } else {
            Write-TdqLog "Installing uv into user-space..."
            if (Invoke-VerifiedRemoteScript -Uri "https://astral.sh/uv/install.ps1" -Label "uv") {
                Ensure-UserPathFront @($LocalBin)
                $uvExe = Resolve-NonStubExe @("uv.exe", "uv")
            }
        }
    }
    $pyExe = Resolve-RealPython
    if (-not $pyExe -and $uvExe) {
        if (Test-DryMode) {
            Write-TdqLog "[dry-run] Would run uv python install --default"
        } else {
            Write-TdqLog "Installing managed Python 3 via uv..."
            & "$uvExe" python install --default | Out-Null
            Ensure-UserPathFront @($LocalBin)
            $pyExe = Resolve-RealPython
        }
    }
    return $pyExe
}

function Resolve-RealPython {
    foreach ($name in @("python3.exe", "python.exe", "py.exe")) {
        $cand = Resolve-NonStubExe @($name)
        if (-not $cand) { continue }
        $checkArgs = if ($name -eq "py.exe") { @("-3", "-c", "import sys; print(sys.version_info[0])") } else { @("-c", "import sys; print(sys.version_info[0])") }
        try {
            $out = & "$cand" @checkArgs 2>$null
            if ($LASTEXITCODE -eq 0 -and ($out -join "") -match '3') {
                return $cand
            }
        } catch {}
    }
    return $null
}

function Ensure-AgyCli {
    $agyDir = Join-Path $env:LOCALAPPDATA "agy\bin"
    $agyExe = Resolve-NonStubExe @("agy.exe", "agy")
    if (-not $agyExe -and (Test-Path -LiteralPath (Join-Path $agyDir "agy.exe"))) {
        $agyExe = Join-Path $agyDir "agy.exe"
        Ensure-UserPathFront @($agyDir)
    }
    if ($agyExe) { return $agyExe }
    if (Test-DryMode) {
        Write-TdqLog "[dry-run] Would install agy CLI from https://antigravity.google/cli/install.ps1"
        return $null
    }
    Write-TdqLog "Attempting user-space agy CLI installation..."
    try {
        if (Invoke-VerifiedRemoteScript -Uri "https://antigravity.google/cli/install.ps1" -Label "agy CLI") {
            Ensure-UserPathFront @($agyDir)
            $agyExe = Resolve-NonStubExe @("agy.exe", "agy")
        }
    } catch {
        Write-TdqLog "agy CLI automatic install unavailable ($($_.Exception.Message)). Install manually from https://antigravity.google/download"
    }
    return $agyExe
}

function Resolve-OrSyncRepo {
    param([string]$GitExe)
    $scriptDir = $PSScriptRoot
    if ($scriptDir) {
        $candidateRoot = Split-Path -Parent $scriptDir
        if ((Test-Path -LiteralPath (Join-Path $candidateRoot "scripts\tdq_setup.py")) -and (Test-Path -LiteralPath (Join-Path $candidateRoot "plugins\tdq-workflow-agy\plugin.json"))) {
            return $candidateRoot
        }
    }
    $targetRepo = Join-Path $env:USERPROFILE ".local\share\tdq-workflow-antigravity"
    if (Test-DryMode) {
        Write-TdqLog "[dry-run] Would clone/update $RepoUrl ($Branch) into $targetRepo"
        return $targetRepo
    }
    if (-not $GitExe) {
        throw "Git is required to clone TDQ-Workflow-Antigravity into $targetRepo"
    }
    $parent = Split-Path -Parent $targetRepo
    if (-not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    if (Test-Path -LiteralPath (Join-Path $targetRepo ".git")) {
        Write-TdqLog "Updating existing checkout at $targetRepo..."
        & "$GitExe" -C "$targetRepo" pull --ff-only
    } else {
        Write-TdqLog "Cloning $RepoUrl into $targetRepo..."
        & "$GitExe" clone --branch "$Branch" -- "$RepoUrl" "$targetRepo"
    }
    return $targetRepo
}

function Invoke-BootstrapSetupScript {
    param([string]$RepoRoot, [string]$PyExe, [string]$TargetStateDir)
    $setupScript = Join-Path $RepoRoot "scripts\tdq_setup.py"
    $setupArgs = @("--setupfully")
    if (-not [string]::IsNullOrWhiteSpace($TargetStateDir)) {
        $setupArgs += @("--state-dir", $TargetStateDir)
    }
    if (Test-DryMode) {
        Write-TdqLog "[dry-run] Would invoke: python -X utf8 `"$setupScript`" $($setupArgs -join ' ')"
        return 0
    }
    if (-not $PyExe) {
        throw "No usable real Python 3 interpreter found (WindowsApps Store stub rejected)."
    }
    if ($PyExe -like "*\py.exe") {
        & "$PyExe" -3 -X utf8 "$setupScript" @setupArgs
    } else {
        & "$PyExe" -X utf8 "$setupScript" @setupArgs
    }
    return $LASTEXITCODE
}

function Invoke-Main {
    if ($Help) {
        Write-Output "Usage: bootstrap.ps1 [-DryRun] [-StateDir <path>] [-KhongChamMay] [-RepoUrl <url>] [-Branch <branch>] [-Yes]"
        return 0
    }
    if (-not (Test-AllowedRepoUrl -Url $RepoUrl)) {
        throw "Rejected untrusted RepoUrl (must match https://github.com/<owner>/<repo>.git): $RepoUrl"
    }
    $localBin = Join-Path $env:USERPROFILE ".local\bin"
    $cargoBin = Join-Path $env:USERPROFILE ".cargo\bin"
    Ensure-UserPathFront @($localBin, $cargoBin)

    $gitExe = Ensure-Git
    $nodeExe = Ensure-FnmAndNode -LocalBin $localBin
    $pyExe = Ensure-UvAndPython -LocalBin $localBin
    $agyExe = Ensure-AgyCli
    $repoRoot = Resolve-OrSyncRepo -GitExe $gitExe

    $probeScript = Join-Path $repoRoot "scripts\tdq_setup_probe.mjs"
    if ($nodeExe -and (Test-Path -LiteralPath $probeScript)) {
        Write-TdqLog "Running Node pre-flight probe..."
        & "$nodeExe" "$probeScript" --json | Out-Null
    }
    $pluginBundle = Join-Path $repoRoot "plugins\tdq-workflow-agy"
    if ($agyExe -and (Test-Path -LiteralPath $pluginBundle)) {
        if (Test-DryMode) {
            Write-TdqLog "[dry-run] Would run agy plugin install `"$pluginBundle`" and enable tdq-workflow-agy"
        } else {
            & "$agyExe" plugin install "$pluginBundle"
            & "$agyExe" plugin enable tdq-workflow-agy
        }
    }
    return Invoke-BootstrapSetupScript -RepoRoot $repoRoot -PyExe $pyExe -TargetStateDir $StateDir
}

if ($MyInvocation.InvocationName -ne '.') {
    $rc = Invoke-Main
    if ($MyInvocation.InvocationName) {
        exit $rc
    }
    if ($rc -ne 0) {
        throw "bootstrap.ps1 failed with exit code $rc"
    }
}
