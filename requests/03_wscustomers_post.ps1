$headers = @{
  "X-API-Key"    = $env:APP_API_KEY
  "Content-Type" = "application/json"
}

$body = @'
{
  "CLIENTES": [
    {
      "A1_CPEDX": "TESTE-001",
      "A1_CGC": "00000000000191"
    }
  ]
}
'@

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/rest/WSCUSTOMERS" `
  -Headers $headers `
  -Body $body
