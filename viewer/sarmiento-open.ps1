param([Parameter(Mandatory=$true,Position=0)][string]$Uri)
$ErrorActionPreference='Stop'
if($Uri -notmatch '^sarmiento://connect/([A-Za-z0-9_-]{3,64})$'){ throw 'Invalid Sarmiento URI' }
$id=$Matches[1]
$paths=@("$env:ProgramFiles\RustDesk\rustdesk.exe","${env:ProgramFiles(x86)}\RustDesk\rustdesk.exe")
$rustdesk=$paths | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if(!$rustdesk){ $cmd=Get-Command rustdesk.exe -ErrorAction SilentlyContinue; if($cmd){$rustdesk=$cmd.Source} }
if(!$rustdesk){ throw 'RustDesk is not installed' }
Start-Process -FilePath $rustdesk -ArgumentList @('--connect',$id)
