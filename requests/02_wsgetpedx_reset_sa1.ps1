$headers = @{ "X-API-Key" = $env:APP_API_KEY }

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/rest/WSGETPEDX?cTabela=SA1&cReset=S" `
  -Headers $headers
