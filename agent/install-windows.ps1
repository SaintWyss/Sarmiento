function Install-SarmientoAgent {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory=$true)][string]$Url,
    [Parameter(Mandatory=$true)][string]$Token,
    [string]$Alias=$env:COMPUTERNAME,
    [string]$RustDeskId='',
    [string]$PermanentPassword='',
    [switch]$SkipRustDeskInstall
  )
  $ErrorActionPreference='Stop'
  $RustDeskVersion='1.4.9'
  $principal=New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
  if(!$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){ throw 'Run PowerShell as Administrator.' }
  $Url=$Url.TrimEnd('/')
  $base="$env:ProgramData\Sarmiento"
  New-Item -ItemType Directory -Force $base | Out-Null
  & icacls.exe $base /inheritance:r /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' | Out-Null
  if($LASTEXITCODE -ne 0){ throw 'Could not secure the Sarmiento agent directory ACL.' }

  function Find-RustDesk {
    $paths=@("$env:ProgramFiles\RustDesk\rustdesk.exe","${env:ProgramFiles(x86)}\RustDesk\rustdesk.exe")
    foreach($path in $paths){ if($path -and (Test-Path $path)){ return $path } }
    return $null
  }

  $rustdesk=Find-RustDesk
  if(!$rustdesk -and !$SkipRustDeskInstall){
    $arch=if($env:PROCESSOR_ARCHITECTURE -eq 'ARM64'){'aarch64'}else{'x86_64'}
    $installer="$env:TEMP\rustdesk-$RustDeskVersion-$arch.exe"
    $download="https://github.com/rustdesk/rustdesk/releases/download/$RustDeskVersion/rustdesk-$RustDeskVersion-$arch.exe"
    Write-Host "Downloading RustDesk $RustDeskVersion..."
    Invoke-WebRequest $download -OutFile $installer -UseBasicParsing
    Start-Process $installer -ArgumentList '--silent-install' -Wait
    Start-Sleep -Seconds 5
    $rustdesk=Find-RustDesk
  }
  if(!$rustdesk){ throw 'RustDesk is not installed. Install it and rerun with -SkipRustDeskInstall.' }

  $public=Invoke-RestMethod -Uri "$Url/api/v1/config/public" -Method Get
  if($public.rustdesk_server){ & $rustdesk --option custom-rendezvous-server $public.rustdesk_server | Out-Null }
  if($public.rustdesk_key){ & $rustdesk --option key $public.rustdesk_key | Out-Null }
  if(!$PermanentPassword){
    $chars='abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'.ToCharArray()
    $bytes=New-Object byte[] 18
    [Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
    $PermanentPassword=-join ($bytes | ForEach-Object { $chars[$_ % $chars.Length] })
  }
  & $rustdesk --password $PermanentPassword | Out-Null
  if(!$RustDeskId){ $RustDeskId=(& $rustdesk --get-id | Select-Object -First 1).Trim() }
  if(!$RustDeskId){ throw 'Could not obtain the RustDesk ID.' }

  $rdVersion=(& $rustdesk --version | Select-Object -First 1)
  $enrollBody=@{
    enrollment_token=$Token; rustdesk_id=$RustDeskId; alias=$Alias; hostname=$env:COMPUTERNAME
    platform='Windows'; architecture=$env:PROCESSOR_ARCHITECTURE; agent_version='1.0.0'
    rustdesk_version=if($rdVersion){$rdVersion}else{'unknown'}
    metadata=@{ os_version=[Environment]::OSVersion.VersionString; user_domain=$env:USERDOMAIN }
  } | ConvertTo-Json -Depth 6
  $enrolled=Invoke-RestMethod -Method Post -Uri "$Url/api/v1/agents/enroll" -ContentType 'application/json' -Body $enrollBody

  Invoke-WebRequest "$Url/agent/sarmiento-agent.ps1" -OutFile "$base\sarmiento-agent.ps1" -UseBasicParsing
  @{
    base_url=$Url; device_id=$enrolled.device_id; agent_token=$enrolled.agent_token
    rustdesk_id=$RustDeskId; heartbeat_interval_seconds=$enrolled.heartbeat_interval_seconds
  } | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 "$base\agent.json"

  $action=New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$base\sarmiento-agent.ps1`" -Mode Run"
  $trigger=New-ScheduledTaskTrigger -AtStartup
  $settings=New-ScheduledTaskSettingsSet -RestartCount 20 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -StartWhenAvailable
  $taskPrincipal=New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
  Register-ScheduledTask -TaskName 'SarmientoAgent' -Action $action -Trigger $trigger -Settings $settings -Principal $taskPrincipal -Force | Out-Null
  Start-ScheduledTask -TaskName 'SarmientoAgent'

  Write-Host ''
  Write-Host "Sarmiento enrolled device $RustDeskId." -ForegroundColor Green
  Write-Host 'RustDesk permanent password (store it in your password manager):' -ForegroundColor Yellow
  Write-Host $PermanentPassword -ForegroundColor Yellow
  Write-Host ''
}
