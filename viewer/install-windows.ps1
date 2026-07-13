function Install-SarmientoViewer {
  [CmdletBinding()]
  param([Parameter(Mandatory=$true)][string]$Url)
  $ErrorActionPreference='Stop'
  $base=Join-Path $env:LOCALAPPDATA 'SarmientoViewer'
  New-Item -ItemType Directory -Force $base | Out-Null
  Invoke-WebRequest "$($Url.TrimEnd('/'))/viewer/sarmiento-open.ps1" -OutFile "$base\sarmiento-open.ps1" -UseBasicParsing
  $root='HKCU:\Software\Classes\sarmiento'
  New-Item -Path $root -Force | Out-Null
  Set-Item -Path $root -Value 'URL:Sarmiento Protocol'
  New-ItemProperty -Path $root -Name 'URL Protocol' -Value '' -PropertyType String -Force | Out-Null
  New-Item -Path "$root\DefaultIcon" -Force | Out-Null
  Set-Item -Path "$root\DefaultIcon" -Value 'powershell.exe,0'
  New-Item -Path "$root\shell\open\command" -Force | Out-Null
  $command="powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File `"$base\sarmiento-open.ps1`" `"%1`""
  Set-Item -Path "$root\shell\open\command" -Value $command
  Write-Host 'Registered sarmiento:// URL handler.' -ForegroundColor Green
}
