# Generate VSTO manifest files with proper hashes
$ErrorActionPreference = "Stop"

$binDir = Join-Path $PSScriptRoot "bin\Release"
$dllPath = Join-Path $binDir "EduPlayPowerPointAddin.dll"

if (!(Test-Path $dllPath)) {
    Write-Error "DLL not found. Build the project first."
    exit 1
}

# Get assembly version
$dll = [System.Reflection.Assembly]::LoadFile($dllPath)
$version = $dll.GetName().Version.ToString()

Write-Host "Generating manifest files for version $version..." -ForegroundColor Green

# Function to compute SHA256 hash
function Get-FileHashBase64 {
    param([string]$FilePath)
    $hash = Get-FileHash -Path $FilePath -Algorithm SHA256
    $bytes = [byte[]] -split ($hash.Hash -replace '..', '0x$& ')
    return [Convert]::ToBase64String($bytes)
}

# Get file sizes and hashes
$dllSize = (Get-Item $dllPath).Length
$dllHash = Get-FileHashBase64 $dllPath
$utilsPath = Join-Path $binDir "Microsoft.Office.Tools.Common.v4.0.Utilities.dll"
$utilsSize = (Get-Item $utilsPath).Length
$utilsHash = Get-FileHashBase64 $utilsPath

# Create .dll.manifest
$dllManifest = @"
<?xml version="1.0" encoding="utf-8"?>
<asmv1:assembly xsi:schemaLocation="urn:schemas-microsoft-com:asm.v1 assembly.adaptive.xsd" manifestVersion="1.0" xmlns:asmv1="urn:schemas-microsoft-com:asm.v1" xmlns="urn:schemas-microsoft-com:asm.v2" xmlns:asmv2="urn:schemas-microsoft-com:asm.v2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:co.v1="urn:schemas-microsoft-com:clickonce.v1" xmlns:asmv3="urn:schemas-microsoft-com:asm.v3" xmlns:dsig="http://www.w3.org/2000/09/xmldsig#" xmlns:co.v2="urn:schemas-microsoft-com:clickonce.v2">
  <asmv1:assemblyIdentity name="EduPlayPowerPointAddin.dll" version="$version" publicKeyToken="0000000000000000" language="neutral" processorArchitecture="msil" type="win32" />
  <application />
  <entryPoint>
    <co.v1:customHostSpecified />
  </entryPoint>
  <trustInfo>
    <security>
      <applicationRequestMinimum>
        <PermissionSet Unrestricted="true" ID="Custom" SameSite="site" />
        <defaultAssemblyRequest permissionSetReference="Custom" />
      </applicationRequestMinimum>
      <requestedPrivileges xmlns="urn:schemas-microsoft-com:asm.v3">
        <requestedExecutionLevel level="asInvoker" uiAccess="false" />
      </requestedPrivileges>
    </security>
  </trustInfo>
  <dependency>
    <dependentOS>
      <osVersionInfo>
        <os majorVersion="5" minorVersion="1" buildNumber="2600" servicePackMajor="0" />
      </osVersionInfo>
    </dependentOS>
  </dependency>
  <dependency>
    <dependentAssembly dependencyType="preRequisite" allowDelayedBinding="true">
      <assemblyIdentity name="Microsoft.Windows.CommonLanguageRuntime" version="4.0.30319.0" />
    </dependentAssembly>
  </dependency>
  <dependency>
    <dependentAssembly dependencyType="install" allowDelayedBinding="true" codebase="EduPlayPowerPointAddin.dll" size="$dllSize">
      <assemblyIdentity name="EduPlayPowerPointAddin" version="$version" language="neutral" processorArchitecture="msil" />
      <hash>
        <dsig:Transforms>
          <dsig:Transform Algorithm="urn:schemas-microsoft-com:HashTransforms.Identity" />
        </dsig:Transforms>
        <dsig:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha256" />
        <dsig:DigestValue>$dllHash</dsig:DigestValue>
      </hash>
    </dependentAssembly>
  </dependency>
  <file name="Microsoft.Office.Tools.Common.v4.0.Utilities.dll" size="$utilsSize">
    <hash>
      <dsig:Transforms>
        <dsig:Transform Algorithm="urn:schemas-microsoft-com:HashTransforms.Identity" />
      </dsig:Transforms>
      <dsig:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha256" />
      <dsig:DigestValue>$utilsHash</dsig:DigestValue>
    </hash>
  </file>
  <vstav3:addIn xmlns:vstav3="urn:schemas-microsoft-com:vsta.v3">
    <vstav3:entryPointsCollection>
      <vstav3:entryPoints>
        <vstav3:entryPoint class="EduPlay.PowerPointAddin.ThisAddIn">
          <assemblyIdentity name="EduPlayPowerPointAddin" version="$version" language="neutral" processorArchitecture="msil" />
        </vstav3:entryPoint>
      </vstav3:entryPoints>
    </vstav3:entryPointsCollection>
    <vstav3:update enabled="false" />
    <vstav3:application>
      <vstov4:customizations xmlns:vstov4="urn:schemas-microsoft-com:vsto.v4">
        <vstov4:customization>
          <vstov4:appAddIn application="PowerPoint" loadBehavior="3" keyName="EduPlayPowerPointAddin">
            <vstov4:friendlyName>EduPlay PowerPoint Add-in</vstov4:friendlyName>
            <vstov4:description>EduPlay PowerPoint Add-in</vstov4:description>
          </vstov4:appAddIn>
        </vstov4:customization>
      </vstov4:customizations>
    </vstav3:application>
  </vstav3:addIn>
</asmv1:assembly>
"@

# Write .dll.manifest
$dllManifestPath = Join-Path $binDir "EduPlayPowerPointAddin.dll.manifest"
[System.IO.File]::WriteAllText($dllManifestPath, $dllManifest, [System.Text.Encoding]::UTF8)

Write-Host "Created: $dllManifestPath" -ForegroundColor Green

# Create .vsto manifest (will be updated by mage.exe with proper hash)
$vstoManifest = @"
<?xml version="1.0" encoding="utf-8"?>
<asmv1:assembly xsi:schemaLocation="urn:schemas-microsoft-com:asm.v1 assembly.adaptive.xsd" manifestVersion="1.0" xmlns:asmv1="urn:schemas-microsoft-com:asm.v1" xmlns="urn:schemas-microsoft-com:asm.v2" xmlns:asmv2="urn:schemas-microsoft-com:asm.v2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:co.v1="urn:schemas-microsoft-com:clickonce.v1" xmlns:asmv3="urn:schemas-microsoft-com:asm.v3" xmlns:dsig="http://www.w3.org/2000/09/xmldsig#" xmlns:co.v2="urn:schemas-microsoft-com:clickonce.v2">
  <asmv1:assemblyIdentity name="EduPlayPowerPointAddin.vsto" version="$version" publicKeyToken="0000000000000000" language="neutral" processorArchitecture="msil" xmlns="urn:schemas-microsoft-com:asm.v1" />
  <description asmv2:publisher="EduPlay" asmv2:product="EduPlay PowerPoint Add-in" xmlns="urn:schemas-microsoft-com:asm.v1" />
  <deployment install="false" />
  <compatibleFrameworks xmlns="urn:schemas-microsoft-com:clickonce.v2">
    <framework targetVersion="4.8" profile="Full" supportedRuntime="4.0.30319" />
  </compatibleFrameworks>
  <dependency>
    <dependentAssembly dependencyType="install" codebase="EduPlayPowerPointAddin.dll.manifest" size="0">
      <assemblyIdentity name="EduPlayPowerPointAddin.dll" version="$version" publicKeyToken="0000000000000000" language="neutral" processorArchitecture="msil" type="win32" />
      <hash>
        <dsig:Transforms>
          <dsig:Transform Algorithm="urn:schemas-microsoft-com:HashTransforms.Identity" />
        </dsig:Transforms>
        <dsig:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha256" />
        <dsig:DigestValue></dsig:DigestValue>
      </hash>
    </dependentAssembly>
  </dependency>
</asmv1:assembly>
"@

$vstoManifestPath = Join-Path $binDir "EduPlayPowerPointAddin.vsto"
[System.IO.File]::WriteAllText($vstoManifestPath, $vstoManifest, [System.Text.Encoding]::UTF8)

Write-Host "Created: $vstoManifestPath" -ForegroundColor Green
Write-Host ""
Write-Host "Now run sign_manifests_complete.ps1 to sign the manifests." -ForegroundColor Cyan

