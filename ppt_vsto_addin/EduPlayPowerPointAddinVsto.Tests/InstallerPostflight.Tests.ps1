Set-StrictMode -Version Latest

$modulePath = Join-Path $PSScriptRoot "..\EduPlayPowerPointAddinVsto\InstallerPostflight.Helpers.ps1"
. $modulePath

Describe "Installer postflight helpers" {
    BeforeEach {
        $script:testRoot = Join-Path $env:TEMP ("EduPlayPostflightTests_" + [guid]::NewGuid().ToString("N"))
        New-Item -Path $script:testRoot -ItemType Directory -Force | Out-Null
        $script:installFolder = Join-Path $script:testRoot "install"
        New-Item -Path $script:installFolder -ItemType Directory -Force | Out-Null
    }

    AfterEach {
        if (Test-Path $script:testRoot) {
            Remove-Item -Path $script:testRoot -Recurse -Force
        }
    }

    It "offers activation when state file is missing and session is interactive" {
        $statePath = Get-ShellExplorerActivationStatePath -InstallFolder $script:installFolder
        $state = Get-ShellExplorerActivationState -StatePath $statePath

        $result = Should-OfferShellExplorerActivation -State $state -IsInteractive $true

        $result | Should Be $true
        $state.Status | Should Be "NotStarted"
    }

    It "does not offer activation after support has already been applied" {
        $statePath = Get-ShellExplorerActivationStatePath -InstallFolder $script:installFolder
        Save-ShellExplorerActivationState -StatePath $statePath -Status "Applied" -Details "Configured"
        $state = Get-ShellExplorerActivationState -StatePath $statePath

        $result = Should-OfferShellExplorerActivation -State $state -IsInteractive $true

        $result | Should Be $false
    }

    It "does not offer activation again after the user declines" {
        $statePath = Get-ShellExplorerActivationStatePath -InstallFolder $script:installFolder
        Save-ShellExplorerActivationState -StatePath $statePath -Status "Declined" -Details "User skipped"
        $state = Get-ShellExplorerActivationState -StatePath $statePath

        $result = Should-OfferShellExplorerActivation -State $state -IsInteractive $true

        $result | Should Be $false
    }

    It "builds elevated activation command with the expected arguments" {
        $statePath = Get-ShellExplorerActivationStatePath -InstallFolder $script:installFolder
        $command = Get-ShellExplorerActivationElevationCommand -InstallFolder $script:installFolder -StatePath $statePath

        $command.FilePath | Should Be ([System.Environment]::ExpandEnvironmentVariables("%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"))
        $command.Arguments | Should Match ([regex]::Escape("-ExecutionPolicy Bypass"))
        $command.Arguments | Should Match ([regex]::Escape("-File"))
        $command.Arguments | Should Match ([regex]::Escape("prepare_activex_environment.ps1"))
        $command.Arguments | Should Match ([regex]::Escape($script:installFolder))
        $command.Arguments | Should Match ([regex]::Escape($statePath))
    }
}
