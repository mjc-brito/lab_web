# Garante que o WSL esta inicializado
wsl --distribution Ubuntu echo "WSL iniciado" | Out-Null

# Detecta o Arduino Due
$device = usbipd list | Select-String "Arduino Due Programming Port"

if (-not $device) {
    Write-Error "Arduino Due nao encontrado. Verifica a ligacao USB."
    exit 1
}

$busid = ($device -split "\s+")[0].Trim()
Write-Host "Arduino encontrado: $busid"

usbipd bind --busid $busid 2>$null
usbipd detach --busid $busid 2>$null
usbipd attach --wsl --busid $busid

if ($LASTEXITCODE -ne 0) {
    Write-Error "Falha ao passar o dispositivo para o WSL."
    exit 1
}

Write-Host "Arduino passado para o WSL com sucesso."

# Configura port forwarding para o WSL
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
& "$scriptDir\port_forward.ps1"