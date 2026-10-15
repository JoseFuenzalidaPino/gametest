# Levanta GAMEZONE accesible desde otros equipos de la misma red.
# Uso:  .\run_lan.ps1            (puerto 8000)
#       .\run_lan.ps1 -Puerto 8080
# Requiere que el puerto esté permitido en el firewall de Windows y que
# DB_PASSWORD (y demás DB_*) estén definidas si MySQL no usa los valores por defecto.
param([int]$Puerto = 8000)

$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { $python = 'python' }

$ips = Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -notmatch '^(127\.|169\.254\.)' -and $_.InterfaceAlias -notmatch 'vEthernet|Loopback' } |
    Select-Object -ExpandProperty IPAddress

# Django solo responde a los hosts permitidos: se agregan las IPs de este equipo
$env:DJANGO_ALLOWED_HOSTS = (@($env:DJANGO_ALLOWED_HOSTS) + $ips | Where-Object { $_ }) -join ','

Write-Host ''
Write-Host 'GAMEZONE disponible en:' -ForegroundColor Green
Write-Host "  Este equipo:  http://localhost:$Puerto/"
foreach ($ip in $ips) { Write-Host "  En la red:    http://${ip}:$Puerto/" }
Write-Host ''

& $python (Join-Path $PSScriptRoot 'manage.py') runserver "0.0.0.0:$Puerto"
