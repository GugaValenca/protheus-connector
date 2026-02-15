# Rode este script antes dos outros:
# .\requests\00_set_env.ps1

param(
  [Parameter(Mandatory=$true)]
  [string]$ApiKey,

  [string]$LocalApiBase = "http://127.0.0.1:8000"
)

$env:APP_API_KEY = $ApiKey
$env:LOCAL_API_BASE = $LocalApiBase

Write-Host "APP_API_KEY e LOCAL_API_BASE configurados nesta sessão."
Write-Host "Exemplo: .\requests\01_wsgetpedx_sa1.ps1"
