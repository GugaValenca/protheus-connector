# Protheus Connector (FastAPI)

API intermediária para integração com TOTVS Protheus via endpoints REST do documento:

- GET `/rest/WSGETPEDX`
- POST `/rest/WSCUSTOMERS` (use `?cAltera=S` para alteração)
- POST `/rest/WSSALESORDERS`

---

## Requisitos

- Python 3.11+
- Acesso ao Protheus REST (URL/porta + credenciais)

---

## Rodar localmente

### 1) Criar venv e instalar dependências

No Windows (PowerShell):

1. Criar ambiente virtual:
   - `python -m venv .venv`

2. Ativar o ambiente:
   - `.\.venv\Scripts\Activate.ps1`

3. Instalar dependências:
   - `pip install -r requirements.txt`

---

### 2) Criar arquivo `.env` (NÃO subir no GitHub)

Crie um arquivo `.env` na raiz do projeto com este exemplo:

APP_NAME=protheus-connector  
APP_ENV=dev  
APP_API_KEY=coloque_sua_chave_aqui

DATABASE_URL=sqlite:///./app.db

PROTHEUS_BASE_URL=http://endereco_servidor:porta  
PROTHEUS_USERNAME=usuario  
PROTHEUS_PASSWORD=senha  
PROTHEUS_TIMEOUT_S=30

---

### 3) Subir a API

- `uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`

Documentação (Swagger):

- http://127.0.0.1:8000/docs

Healthcheck:

- http://127.0.0.1:8000/health

---

---

## Rodar com Docker

1. Configure o `.env` (use o `.env.example` como base)

2. Subir com Docker Compose:

- docker compose up --build

3. Acessar:

- Health: http://127.0.0.1:8000/health
- Docs: http://127.0.0.1:8000/docs

---

---

## Testes (PowerShell)

### 1) Configurar a API Key na sessão (sem gravar no repo)

- `.\requests\00_set_env.ps1 -ApiKey "SUA_CHAVE_AQUI"`

Opcional (se quiser trocar a base local):

- `.\requests\00_set_env.ps1 -ApiKey "SUA_CHAVE_AQUI" -LocalApiBase "http://127.0.0.1:8000"`

---

### 2) Rodar scripts de teste

- `.\requests\01_wsgetpedx_sa1.ps1`
- `.\requests\02_wsgetpedx_reset_sa1.ps1`
- `.\requests\03_wscustomers_post.ps1`
- `.\requests\04_wscustomers_put.ps1`
- `.\requests\05_wssalesorders_post.ps1`

---

## Observações importantes

- Se o Protheus estiver inacessível (URL/porta errada, sem VPN, serviço fora do ar), você pode ver erro 502 com WinError 10061.
- Os payloads de exemplo dos scripts podem precisar de ajustes conforme as regras/validações do Protheus do cliente.
