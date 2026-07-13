param(
  [ValidateSet('Run','Once','ReplaceToken')][string]$Mode='Run',
  [string]$ConfigPath="$env:ProgramData\Sarmiento\agent.json",
  [string]$NewToken=''
)
$ErrorActionPreference='Stop'
$AgentVersion='1.1.0'

function Write-AgentLog([string]$Message){ Write-Host "[sarmiento-agent] $Message" }
function Read-AgentConfig { if(!(Test-Path $ConfigPath)){ throw "Agent is not enrolled; config missing at $ConfigPath" }; Get-Content $ConfigPath -Raw | ConvertFrom-Json }
function Write-AgentConfig($Config){ $dir=Split-Path $ConfigPath; New-Item -ItemType Directory -Force $dir | Out-Null; $Config | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 $ConfigPath }
function Assert-SarmientoUrl([string]$Value){
  $uri=$null
  if(![Uri]::TryCreate($Value,[UriKind]::Absolute,[ref]$uri)){ throw 'Sarmiento URL must be absolute.' }
  if($uri.Scheme -notin @('http','https')){ throw 'Sarmiento URL must use HTTP(S).' }
  if($uri.UserInfo -or $uri.Fragment){ throw 'Sarmiento URL must not contain credentials or a fragment.' }
  if($uri.Scheme -eq 'http' -and !$uri.IsLoopback){ throw 'Plain HTTP is allowed only for loopback.' }
  return $uri.AbsoluteUri.TrimEnd('/')
}
function Get-RustDeskPath {
  $paths=@("$env:ProgramFiles\RustDesk\rustdesk.exe","${env:ProgramFiles(x86)}\RustDesk\rustdesk.exe")
  foreach($path in $paths){ if($path -and (Test-Path $path)){ return $path } }
  $cmd=Get-Command rustdesk.exe -ErrorAction SilentlyContinue
  if($cmd){ return $cmd.Source }
  throw 'RustDesk is not installed'
}
function Get-HeartbeatBody($RustDeskId){
  $rd=Get-RustDeskPath
  $rdVersion=(& $rd --version | Select-Object -First 1)
  return @{
    rustdesk_id=$RustDeskId
    hostname=$env:COMPUTERNAME
    platform='Windows'
    architecture=$env:PROCESSOR_ARCHITECTURE
    agent_version=$AgentVersion
    rustdesk_version=if($rdVersion){$rdVersion}else{'unknown'}
    metadata=@{ os_version=[Environment]::OSVersion.VersionString; user_domain=$env:USERDOMAIN }
  }
}
function Send-Heartbeat {
  $config=Read-AgentConfig
  $baseUrl=Assert-SarmientoUrl ([string]$config.base_url)
  $headers=@{ Authorization="Bearer $($config.agent_token)" }
  $body=(Get-HeartbeatBody $config.rustdesk_id) | ConvertTo-Json -Depth 6
  $response=Invoke-RestMethod -Method Post -Uri "$baseUrl/api/v1/agents/heartbeat" -Headers $headers -ContentType 'application/json' -Body $body
  if($response.credential_rotation_required){
    $rotated=Invoke-RestMethod -Method Post -Uri "$baseUrl/api/v1/agents/rotate-token" -Headers $headers -ContentType 'application/json'
    $config.agent_token=$rotated.agent_token
    Write-AgentConfig $config
    Write-AgentLog 'Agent credential rotated automatically'
  }
}

if($Mode -eq 'ReplaceToken'){
  if(!$NewToken){ throw 'NewToken is required' }
  $config=Read-AgentConfig; $config.agent_token=$NewToken; Write-AgentConfig $config; Write-AgentLog 'Agent credential updated'; exit 0
}
if($Mode -eq 'Once'){ Send-Heartbeat; exit 0 }
$failures=0
while($true){
  try { Send-Heartbeat; $failures=0; Start-Sleep -Seconds 30 }
  catch { $failures++; $delay=[Math]::Min(300,[Math]::Max(30,[Math]::Pow(2,[Math]::Min($failures,8)))); Write-AgentLog "Heartbeat failed: $($_.Exception.Message); retrying in $delay seconds"; Start-Sleep -Seconds $delay }
}
