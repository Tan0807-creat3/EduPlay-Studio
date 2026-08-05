function Get-ShellExplorerActivationStatePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$InstallFolder
    )

    $reportsFolder = Join-Path $InstallFolder "reports"
    return Join-Path $reportsFolder "shell-explorer-activation-state.json"
}

function Get-ShellExplorerActivationState {
    param(
        [Parameter(Mandatory = $true)]
        [string]$StatePath
    )

    if (-not (Test-Path $StatePath)) {
        return [pscustomobject]@{
            Status = "NotStarted"
            Details = ""
            UpdatedAtUtc = $null
        }
    }

    try {
        return Get-Content -LiteralPath $StatePath -Raw | ConvertFrom-Json
    } catch {
        return [pscustomobject]@{
            Status = "Unknown"
            Details = $_.Exception.Message
            UpdatedAtUtc = $null
        }
    }
}

function Save-ShellExplorerActivationState {
    param(
        [Parameter(Mandatory = $true)]
        [string]$StatePath,

        [Parameter(Mandatory = $true)]
        [string]$Status,

        [string]$Details = ""
    )

    $stateDir = Split-Path -Parent $StatePath
    if (-not [string]::IsNullOrWhiteSpace($stateDir)) {
        New-Item -Path $stateDir -ItemType Directory -Force | Out-Null
    }

    [pscustomobject]@{
        Status = $Status
        Details = $Details
        UpdatedAtUtc = [DateTime]::UtcNow.ToString("o")
    } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $StatePath -Encoding UTF8
}

function Should-OfferShellExplorerActivation {
    param(
        [Parameter(Mandatory = $true)]
        [psobject]$State,

        [Parameter(Mandatory = $true)]
        [bool]$IsInteractive
    )

    return $false
}

function Get-ShellExplorerActivationElevationCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$InstallFolder,

        [Parameter(Mandatory = $true)]
        [string]$StatePath
    )

    return $null
}
