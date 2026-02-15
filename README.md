# Protheus Connector (PedX ↔ TOTVS Protheus)

API intermediária em FastAPI para integrar com TOTVS Protheus via endpoints:
- GET /rest/WSGETPEDX
- POST /rest/WSCUSTOMERS
- POST /rest/WSSALESORDERS

## Requisitos
- Python 3.11+
- VSCode

## Rodar local
1) Crie o .env baseado no .env.example
2) Instale dependências: `pip install -r requirements.txt`
3) Rode: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

## Autenticação da API
Use o header:
- `X-API-Key: <APP_API_KEY>`
