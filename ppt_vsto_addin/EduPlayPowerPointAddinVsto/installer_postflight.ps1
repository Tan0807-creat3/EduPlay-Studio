param(
    [string]$InstallFolder = ""
)

$ErrorActionPreference = "Stop"

function Write-PostflightLogLine {
    param(
        [string]$Message
    )

    if ([string]::IsNullOrWhiteSpace($script:LogPath)) {
        return
    }

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $script:LogPath -Value ("[" + $timestamp + "] " + $Message) -Encoding UTF8
}

function Add-ReportEntry {
    param(
        [System.Collections.Generic.List[object]]$Report,
        [string]$Step,
        [string]$Status,
        [string]$Details
    )

    $Report.Add([pscustomobject]@{
        Step = $Step
        Status = $Status
        Details = $Details
    })
}

function Get-RegistryValueOrNull {
    param(
        [string]$Path,
        [string]$Name
    )

    try {
        return Get-ItemPropertyValue -Path $Path -Name $Name -ErrorAction Stop
    } catch {
        return $null
    }
}

function Find-TrustedLocation {
    param(
        [string]$BasePath,
        [string]$TargetPath
    )

    if (-not (Test-Path $BasePath)) {
        return $false
    }

    $normalizedTarget = $TargetPath.TrimEnd('\')
    foreach ($candidate in Get-ChildItem -Path $BasePath -ErrorAction SilentlyContinue) {
        $candidatePath = Get-RegistryValueOrNull -Path $candidate.PSPath -Name "Path"
        if (-not [string]::IsNullOrWhiteSpace($candidatePath) -and $candidatePath.TrimEnd('\') -eq $normalizedTarget) {
            return $true
        }
    }

    return $false
}

function Resolve-ExistingPath {
    param(
        [string[]]$Candidates
    )

    foreach ($candidate in $Candidates) {
        if (-not [string]::IsNullOrWhiteSpace($candidate) -and (Test-Path $candidate)) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    return $null
}

$helperCandidates = @(
    (Join-Path $PSScriptRoot "InstallerPostflight.Helpers.ps1")
)
if (-not [string]::IsNullOrWhiteSpace($InstallFolder)) {
    $helperCandidates += (Join-Path $InstallFolder "InstallerPostflight.Helpers.ps1")
}
$helperPath = Resolve-ExistingPath -Candidates $helperCandidates
if ($helperPath) {
    . $helperPath
}

function Test-IsInteractiveSession {
    try {
        return [Environment]::UserInteractive
    } catch {
        return $false
    }
}

function Show-ShellExplorerActivationPrompt {
    Add-Type -AssemblyName System.Windows.Forms
    $message = "EduPlay co the thu bat che do tuong thich Shell.Explorer.2 cho PowerPoint.`r`n`r`nBuoc nay can quyen Admin va chi can xac nhan mot lan. Ban co muon tiep tuc khong?"
    $caption = "EduPlay PowerPoint Add-in"
    return [System.Windows.Forms.MessageBox]::Show(
        $message,
        $caption,
        [System.Windows.Forms.MessageBoxButtons]::YesNo,
        [System.Windows.Forms.MessageBoxIcon]::Question)
}

function Invoke-ShellExplorerActivationFlow {
    param(
        [System.Collections.Generic.List[object]]$Report,
        [string]$ResolvedInstallFolder
    )

    if (-not (Get-Command Get-ShellExplorerActivationStatePath -ErrorAction SilentlyContinue)) {
        Add-ReportEntry -Report $Report -Step "Shell.Explorer.2 consent" -Status "Skipped" -Details "Helper script not available."
        return
    }

    $statePath = Get-ShellExplorerActivationStatePath -InstallFolder $ResolvedInstallFolder
    $state = Get-ShellExplorerActivationState -StatePath $statePath
    Add-ReportEntry -Report $Report -Step "Shell.Explorer.2 consent state" -Status "Observed" -Details ("Status=" + $state.Status + "; Details=" + $state.Details)

    if (-not (Should-OfferShellExplorerActivation -State $state -IsInteractive (Test-IsInteractiveSession))) {
        Add-ReportEntry -Report $Report -Step "Shell.Explorer.2 consent" -Status "Skipped" -Details "Interactive prompt is not required."
        return
    }

    $promptResult = Show-ShellExplorerActivationPrompt
    if ($promptResult -ne [System.Windows.Forms.DialogResult]::Yes) {
        Save-ShellExplorerActivationState -StatePath $statePath -Status "Declined" -Details "User declined after MSI install."
        Add-ReportEntry -Report $Report -Step "Shell.Explorer.2 consent" -Status "Declined" -Details "User skipped compatibility activation."
        return
    }

    $command = Get-ShellExplorerActivationElevationCommand -InstallFolder $ResolvedInstallFolder -StatePath $statePath
    Save-ShellExplorerActivationState -StatePath $statePath -Status "PendingElevation" -Details "Waiting for elevated compatibility configuration."
    Write-PostflightLogLine ("Launching elevated compatibility step: " + $command.Arguments)

    try {
        $process = Start-Process -FilePath $command.FilePath -ArgumentList $command.Arguments -Verb RunAs -Wait -PassThru
    } catch [System.ComponentModel.Win32Exception] {
        Save-ShellExplorerActivationState -StatePath $statePath -Status "ElevationCanceled" -Details $_.Exception.Message
        Add-ReportEntry -Report $Report -Step "Shell.Explorer.2 consent" -Status "Canceled" -Details "UAC elevation was canceled."
        return
    }

    $updatedState = Get-ShellExplorerActivationState -StatePath $statePath
    $details = "ExitCode=$($process.ExitCode); State=$($updatedState.Status); Details=$($updatedState.Details)"
    if ($process.ExitCode -eq 0 -and $updatedState.Status -eq "Applied") {
        Add-ReportEntry -Report $Report -Step "Shell.Explorer.2 compatibility" -Status "Applied" -Details $details
        return
    }

    Add-ReportEntry -Report $Report -Step "Shell.Explorer.2 compatibility" -Status "Failed" -Details $details
}

$initialRoot = Resolve-ExistingPath -Candidates @(
    $InstallFolder,
    $PSScriptRoot
)

$fallbackRoot = if ($initialRoot) { $initialRoot } else { $env:TEMP }
$fallbackReportDir = Join-Path $fallbackRoot "reports"
New-Item -Path $fallbackReportDir -ItemType Directory -Force | Out-Null
$script:LogPath = Join-Path $fallbackReportDir "installer-postflight.log"
Write-PostflightLogLine "Installer postflight started."

try {
    $report = New-Object 'System.Collections.Generic.List[object]'
    $resolvedInstallFolder = Resolve-ExistingPath -Candidates @(
        $InstallFolder,
        $PSScriptRoot
    )

    if (-not $resolvedInstallFolder) {
        throw "Cannot resolve install folder from '$InstallFolder' or '$PSScriptRoot'."
    }

    $manifestPath = Join-Path $resolvedInstallFolder "EduPlayPowerPointAddin.vsto"
    $certFile = Join-Path $resolvedInstallFolder "EduPlayPowerPointAddinVsto.cer"
    $trustedSlidesFolder = Join-Path $resolvedInstallFolder "TrustedSlides"
    $reportDir = Join-Path $resolvedInstallFolder "reports"
    $reportPath = Join-Path $reportDir ("installer-postflight-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".json")

    New-Item -Path $reportDir -ItemType Directory -Force | Out-Null
    $script:LogPath = Join-Path $reportDir "installer-postflight.log"
    Write-PostflightLogLine "Resolved install folder: $resolvedInstallFolder"

    Add-ReportEntry -Report $report -Step "Install folder" -Status "Observed" -Details $resolvedInstallFolder

    if (Test-Path $manifestPath) {
        Add-ReportEntry -Report $report -Step "Manifest file" -Status "Observed" -Details $manifestPath
    } else {
        Add-ReportEntry -Report $report -Step "Manifest file" -Status "Missing" -Details $manifestPath
    }

    if (Test-Path $certFile) {
        try {
            $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($certFile)
            [System.Environment]::SetEnvironmentVariable("EDUPLAY_VSTO_CERT_THUMBPRINT", $cert.Thumbprint, "User")
            Add-ReportEntry -Report $report -Step "Environment variable" -Status "Applied" -Details "Set EDUPLAY_VSTO_CERT_THUMBPRINT=$($cert.Thumbprint)"
        } catch {
            Add-ReportEntry -Report $report -Step "Environment variable" -Status "Failed" -Details $_.Exception.Message
        }
    } else {
        Add-ReportEntry -Report $report -Step "Environment variable" -Status "Skipped" -Details "Missing certificate file: $certFile"
    }

    [System.Environment]::SetEnvironmentVariable("EDUPLAY_ADDIN_INSTALL_ROOT", $resolvedInstallFolder, "User")
    Add-ReportEntry -Report $report -Step "Install root variable" -Status "Applied" -Details "Set EDUPLAY_ADDIN_INSTALL_ROOT=$resolvedInstallFolder"

    Invoke-ShellExplorerActivationFlow -Report $report -ResolvedInstallFolder $resolvedInstallFolder

    $addinKey = "HKCU:\Software\Microsoft\Office\PowerPoint\Addins\EduPlayPowerPointAddin"
    $manifestValue = Get-RegistryValueOrNull -Path $addinKey -Name "Manifest"
    $loadBehavior = Get-RegistryValueOrNull -Path $addinKey -Name "LoadBehavior"
    if ($manifestValue) {
        Add-ReportEntry -Report $report -Step "Add-in registration" -Status "Observed" -Details "Manifest=$manifestValue; LoadBehavior=$loadBehavior"
    } else {
        Add-ReportEntry -Report $report -Step "Add-in registration" -Status "Missing" -Details $addinKey
    }

    $trustedTargets = @(
        @{ Label = "Install folder trusted location"; Path = $resolvedInstallFolder },
        @{ Label = "TrustedSlides trusted location"; Path = $trustedSlidesFolder }
    )

    $officeVersions = @("16.0", "15.0", "14.0", "12.0")
    foreach ($target in $trustedTargets) {
        if (-not (Test-Path $target.Path)) {
            Add-ReportEntry -Report $report -Step $target.Label -Status "Skipped" -Details "Missing path: $($target.Path)"
            continue
        }

        $found = $false
        foreach ($version in $officeVersions) {
            $trustedBasePath = "HKCU:\Software\Microsoft\Office\$version\PowerPoint\Security\Trusted Locations"
            if (Find-TrustedLocation -BasePath $trustedBasePath -TargetPath $target.Path) {
                $found = $true
                Add-ReportEntry -Report $report -Step $target.Label -Status "Observed" -Details "Found under Office $version"
            }
        }

        if (-not $found) {
            Add-ReportEntry -Report $report -Step $target.Label -Status "Missing" -Details $target.Path
        }
    }

    $securityChecks = @(
        @{ Path = "HKCU:\Software\Microsoft\Office\Common\Security"; Name = "DisableAllActiveX"; Label = "User DisableAllActiveX" },
        @{ Path = "HKCU:\Software\Microsoft\Office\16.0\Common\Security"; Name = "UFIControls"; Label = "User UFIControls 16.0" },
        @{ Path = "HKCU:\Software\Microsoft\Office\15.0\Common\Security"; Name = "UFIControls"; Label = "User UFIControls 15.0" },
        @{ Path = "HKCU:\Software\Microsoft\Office\14.0\Common\Security"; Name = "UFIControls"; Label = "User UFIControls 14.0" },
        @{ Path = "HKCU:\Software\Microsoft\Office\12.0\Common\Security"; Name = "UFIControls"; Label = "User UFIControls 12.0" }
    )

    foreach ($check in $securityChecks) {
        $value = Get-RegistryValueOrNull -Path $check.Path -Name $check.Name
        if ($null -ne $value) {
            Add-ReportEntry -Report $report -Step $check.Label -Status "Observed" -Details "$($check.Path) -> $($check.Name) = $value"
        } else {
            Add-ReportEntry -Report $report -Step $check.Label -Status "NotSet" -Details "$($check.Path) -> $($check.Name)"
        }
    }

    try {
        $config = Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Office\ClickToRun\Configuration" -ErrorAction Stop
        Add-ReportEntry -Report $report -Step "Office build" -Status "Observed" -Details "Platform=$($config.Platform); Version=$($config.VersionToReport); Product=$($config.ProductReleaseIds)"
    } catch {
        Add-ReportEntry -Report $report -Step "Office build" -Status "Unknown" -Details $_.Exception.Message
    }

    try {
        $clsid = (Get-ItemProperty "Registry::HKEY_CLASSES_ROOT\Shell.Explorer.2\CLSID" -ErrorAction Stop)."(default)"
        Add-ReportEntry -Report $report -Step "Shell.Explorer.2 registration" -Status "Observed" -Details "CLSID=$clsid"
    } catch {
        Add-ReportEntry -Report $report -Step "Shell.Explorer.2 registration" -Status "Missing" -Details $_.Exception.Message
    }

    $policyChecks = @(
        @{ Path = "HKCU:\Software\Policies\Microsoft\Office\Common\Security"; Name = "DisableAllActiveX"; Label = "Policy DisableAllActiveX" },
        @{ Path = "HKCU:\Software\Policies\Microsoft\Office\16.0\Common\Security"; Name = "UFIControls"; Label = "Policy UFIControls 16.0" },
        @{ Path = "HKCU:\Software\Policies\Microsoft\Office\16.0\PowerPoint\Security"; Name = "VBAWarnings"; Label = "Policy VBAWarnings" },
        @{ Path = "HKCU:\Software\Policies\Microsoft\Office\16.0\PowerPoint\Security\ProtectedView"; Name = "DisableAttachmentsInPV"; Label = "Policy ProtectedView Attachments" }
    )

    foreach ($check in $policyChecks) {
        $value = Get-RegistryValueOrNull -Path $check.Path -Name $check.Name
        if ($null -ne $value) {
            Add-ReportEntry -Report $report -Step $check.Label -Status "Observed" -Details "$($check.Path) -> $($check.Name) = $value"
        } else {
            Add-ReportEntry -Report $report -Step $check.Label -Status "NotSet" -Details "$($check.Path) -> $($check.Name)"
        }
    }

    $report | ConvertTo-Json -Depth 4 | Set-Content -Path $reportPath -Encoding UTF8
    Write-PostflightLogLine "Installer postflight report written to $reportPath"
} catch {
    Write-PostflightLogLine ("Installer postflight failed: " + $_.Exception.Message)
    Write-PostflightLogLine $_.ScriptStackTrace
    throw
}
