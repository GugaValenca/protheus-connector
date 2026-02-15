$headers = @{
  "X-API-Key"    = $env:APP_API_KEY
  "Content-Type" = "application/json"
}

$body = @'
{
  "PEDIDOS": [
    {
      "C5_NUMEXT": "PED-TESTE-001",
      "ITENS": [
        {
          "C6_PRODUTO": "000000000000000",
          "C6_QTDVEN": 1
        }
      ]
    }
  ]
}
'@

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/rest/WSSALESORDERS" `
  -Headers $headers `
  -Body $body
