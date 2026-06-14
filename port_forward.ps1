$wsl_ip = (wsl -e bash -c "ip addr show eth0 | grep 'inet ' | awk '{print `$2}' | cut -d/ -f1").Trim()

if (-not $wsl_ip) {
    Write-Error "Nao foi possivel obter o IP do WSL."
    exit 1
}

Write-Host "IP do WSL: $wsl_ip"

netsh interface portproxy delete v4tov4 listenport=8000 listenaddress=0.0.0.0 2>$null
netsh interface portproxy delete v4tov4 listenport=8443 listenaddress=0.0.0.0 2>$null

netsh interface portproxy add v4tov4 listenport=8000 listenaddress=0.0.0.0 connectport=8000 connectaddress=$wsl_ip
netsh interface portproxy add v4tov4 listenport=8443 listenaddress=0.0.0.0 connectport=8443 connectaddress=$wsl_ip

Write-Host "Port forwarding configurado para $wsl_ip"