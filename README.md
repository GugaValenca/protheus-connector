# Protheus Connector (TOTVS Protheus Integration)

A connector built with **FastAPI** to integrate with **TOTVS Protheus** services (WSGETPEDX, WSCUSTOMERS, WSSALESORDERS).  
Includes **API Key authentication**, **idempotency**, **sync logging**, and **local persistence** for mapping and runs.

---

## ✨ Features

- 🔐 API Key Authentication (`X-API-Key`)
- 🔄 WSGETPEDX integration (pull/reset/filter/period)
- 👤 Customers integration (`WSCUSTOMERS`) with create/update support
- 🧾 Sales Orders integration (`WSSALESORDERS`)
- ♻️ Idempotency to avoid duplicated operations
- 🗃️ SQLite persistence for:
  - idempotency cache
  - entity mapping (source → Protheus ids)
  - sync runs history
- 📚 Swagger UI / OpenAPI docs (`/docs`)
- 🐳 Docker support (Dockerfile + docker-compose)

---

## 🛠️ Tech Stack

### Backend

![Python](https://img.shields.io/badge/Python-000?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-000?logo=fastapi&logoColor=white)
![Uvicorn](https://img.shields.io/badge/Uvicorn-000?logo=uvicorn&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-000?logo=pydantic&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-000?logo=sqlalchemy&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-000?logo=sqlite&logoColor=white)
![HTTPX](https://img.shields.io/badge/HTTPX-000?logo=python&logoColor=white)

### Tools / DevOps

![Docker](https://img.shields.io/badge/Docker-000?logo=docker&logoColor=white)
![Git](https://img.shields.io/badge/Git-000?logo=git&logoColor=white)
![GitHub](https://img.shields.io/badge/GitHub-000?logo=github&logoColor=white)

---

## ✅ Prerequisites

- Python **3.10+**
- Git
- (Optional) Docker Desktop

---

## 📦 Installation

### 1) Clone repository

```bash
git clone https://github.com/GugaValenca/protheus-connector.git
cd protheus-connector
```

### 2) Create virtual environment

```bash
python -m venv .venv
```

**Windows (PowerShell)**

```powershell
.\.venv\Scripts\Activate.ps1
```

**Mac/Linux**

```bash
source .venv/bin/activate
```

### 3) Install dependencies

```bash
pip install -r requirements.txt
```

---

## 🔧 Environment Variables

Create a `.env` file in the project root (use `.env.example` as base):

```env
APP_NAME=protheus-connector
APP_ENV=dev
APP_API_KEY=DeveloperKey123

DATABASE_URL=sqlite:///./app.db

PROTHEUS_BASE_URL=http://<host>:<port>
PROTHEUS_USERNAME=<user>
PROTHEUS_PASSWORD=<password>
PROTHEUS_TIMEOUT_S=30
```

> ✅ Keep `.env` out of GitHub. It is already ignored by `.gitignore`.

---

## ▶️ Running (Local)

Start the API:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Access:

- Health: http://127.0.0.1:8000/health
- Docs: http://127.0.0.1:8000/docs

---

## 🐳 Running with Docker

1. Configure `.env` (use `.env.example`)

2. Start with Docker Compose:

```bash
docker compose up --build
```

3. Access:

- Health: http://127.0.0.1:8000/health
- Docs: http://127.0.0.1:8000/docs

---

## 🔐 Authentication

Protected endpoints require:

```
X-API-Key: <your_api_key>
```

Example (PowerShell):

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/meta/protheus" -Headers @{ "X-API-Key" = "DeveloperKey123" }
```

---

## 🧪 Quick Tests

### WSGETPEDX (SA1)

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/rest/WSGETPEDX?cTabela=SA1" `
  -Headers @{ "X-API-Key" = "DeveloperKey123" }
```

### Create Customer (WSCUSTOMERS)

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/customers" `
  -Headers @{ "X-API-Key" = "DeveloperKey123"; "Content-Type" = "application/json" } `
  -Body '{"CLIENTES":[{"A1_CPEDX":"TESTE-001","A1_CGC":"00000000000191"}]}'
```

> If Protheus is not reachable, the API may return **502 Bad Gateway** (connection refused).  
> Protheus access often requires internal network/VPN permissions.

---

## 🔌 Main Endpoints

### Health / Meta

- `GET /health`
- `GET /meta/protheus` (protected)

### WSGETPEDX / Sync

- `POST /sync/reset/{table}`
- `POST /sync/pull`
- `POST /sync/pull/filter`
- `POST /sync/pull/orders`
- `POST /sync/pull/invoices`
- `GET  /rest/WSGETPEDX`

### Customers

- `POST /customers`
- `PUT  /customers`
- `POST /rest/WSCUSTOMERS` (Protheus-compatible)

### Sales Orders

- `POST /salesorders`
- `POST /rest/WSSALESORDERS` (Protheus-compatible)

---

## 🗂️ Project Structure

```text
protheus-connector/
├── app/
│   ├── main.py               # FastAPI app and routes
│   ├── settings.py           # Environment settings
│   ├── security.py           # API key auth
│   ├── db.py                 # SQLAlchemy engine/session/base
│   ├── models.py             # Database models
│   ├── schemas.py            # Pydantic schemas
│   ├── protheus_client.py    # Protheus HTTP client (httpx)
│   ├── services/
│   │   ├── sync_service.py
│   │   ├── customer_service.py
│   │   └── order_service.py
│   └── utils.py
├── requests/                 # PowerShell test scripts
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
└── README.md
```

---

## 📌 Notes

- This project follows the integration requirements described in the provided document.
- Real Protheus testing depends on:
  - correct BASE_URL and port
  - VPN/internal network access
  - firewall rules
  - service availability

---

## License 📄

This project is licensed under the MIT License.

## Contact 📬

**Gustavo Valença**

[![GitHub](https://img.shields.io/badge/github-%23121011.svg?style=for-the-badge&logo=github&logoColor=white)](https://github.com/GugaValenca)
[![LinkedIn](https://img.shields.io/badge/linkedin-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/gugavalenca/)
[![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?style=for-the-badge&logo=Instagram&logoColor=white)](https://www.instagram.com/gugatampa)
[![Twitch](https://img.shields.io/badge/Twitch-%239146FF.svg?style=for-the-badge&logo=Twitch&logoColor=white)](https://www.twitch.tv/gugatampa)
[![Discord](https://img.shields.io/badge/Discord-%235865F2.svg?style=for-the-badge&logo=discord&logoColor=white)](https://discord.com/invite/3QQyR5whBZ)

---

⭐ **If you found this project helpful, please give it a star!**
