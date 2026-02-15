import httpx
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from .db import Base, get_engine, get_session_factory
from .protheus_client import ProtheusClient, ProtheusConfig
from .schemas import CustomerBody, FilterRequest, PeriodRequest, PullRequest, SalesOrderBody
from .security import require_api_key
from .services import sync_service
from .services.customer_service import get_idem, save_idem, upsert_mapping_customer
from .services.order_service import (
    apply_order_defaults,
    build_idempotency_key,
    find_idem,
    save_idem as save_idem_order,
    upsert_mapping_order,
)
from .settings import settings


engine = get_engine(settings.DATABASE_URL)
SessionLocal = get_session_factory(engine)
Base.metadata.create_all(bind=engine)

protheus = ProtheusClient(
    ProtheusConfig(
        base_url=settings.PROTHEUS_BASE_URL,
        username=settings.PROTHEUS_USERNAME,
        password=settings.PROTHEUS_PASSWORD,
        timeout_s=settings.PROTHEUS_TIMEOUT_S,
    )
)

app = FastAPI(title=settings.APP_NAME)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok", "env": settings.APP_ENV}


@app.get("/meta/protheus", dependencies=[Depends(require_api_key)])
def meta_protheus():
    """
    Metadados dos endpoints Protheus usados pelo conector,
    conforme documento de integração.
    """
    return {
        "wsgetpedx_tables": ["SA1", "SA3", "SA4", "SB1", "DA1", "SE4", "SC5", "SF2"],
        "customers": {"create": "/rest/WSCUSTOMERS", "update": "/rest/WSCUSTOMERS?cAltera=S"},
        "salesorders": {"create": "/rest/WSSALESORDERS"},
    }


@app.post("/sync/reset/{table}", dependencies=[Depends(require_api_key)])
def sync_reset(table: str, db: Session = Depends(get_db)):
    """
    Reseta o controle de listagem do Protheus para tabelas que suportam cReset=S.
    """
    try:
        t = sync_service.ensure_table(table)
        data = protheus.get_wsgetpedx(t, reset=True)

        sync_service.store_raw(db, t, {"reset_response": data})
        sync_service.log_run(db, t, "reset", "success", {"response": data})
        return data

    except ValueError as e:
        sync_service.log_run(db, (table or "").upper(), "reset", "error", {"error": str(e)})
        raise HTTPException(status_code=400, detail=str(e)) from e

    except httpx.HTTPError as e:
        sync_service.log_run(db, (table or "").upper(), "reset", "error", {"error": str(e)})
        raise HTTPException(status_code=502, detail=str(e)) from e


@app.post("/sync/pull", dependencies=[Depends(require_api_key)])
def sync_pull(req: PullRequest, db: Session = Depends(get_db)):
    """
    Puxa lote incremental de uma tabela (sem filtro), opcionalmente com reset.
    """
    try:
        t = sync_service.ensure_table(req.table)
        data = protheus.get_wsgetpedx(t, reset=req.reset)

        sync_service.store_raw(db, t, {"pull_response": data})
        sync_service.log_run(db, t, "pull", "success", {"reset": req.reset})
        return data

    except ValueError as e:
        sync_service.log_run(db, (req.table or "").upper(), "pull", "error", {"error": str(e)})
        raise HTTPException(status_code=400, detail=str(e)) from e

    except httpx.HTTPError as e:
        sync_service.log_run(db, (req.table or "").upper(), "pull", "error", {"error": str(e)})
        raise HTTPException(status_code=502, detail=str(e)) from e


@app.post("/sync/pull/filter", dependencies=[Depends(require_api_key)])
def sync_pull_filter(req: FilterRequest, db: Session = Depends(get_db)):
    """
    Puxa dados com filtro cCampo/cValor.
    Ex: SA1 com A1_CGC.
    """
    try:
        t = sync_service.ensure_table(req.table)
        if not req.campo.strip() or not req.valor.strip():
            raise ValueError("campo/valor não podem ser vazios.")

        data = protheus.get_wsgetpedx(t, campo=req.campo.strip(), valor=req.valor.strip())

        sync_service.store_raw(db, t, {"filter": {"campo": req.campo, "valor": req.valor}, "response": data})
        sync_service.log_run(db, t, "pull_filter", "success", {"campo": req.campo, "valor": req.valor})
        return data

    except ValueError as e:
        sync_service.log_run(db, (req.table or "").upper(), "pull_filter", "error", {"error": str(e)})
        raise HTTPException(status_code=400, detail=str(e)) from e

    except httpx.HTTPError as e:
        sync_service.log_run(db, (req.table or "").upper(), "pull_filter", "error", {"error": str(e)})
        raise HTTPException(status_code=502, detail=str(e)) from e


@app.post("/sync/pull/orders", dependencies=[Depends(require_api_key)])
def sync_orders(req: PeriodRequest, db: Session = Depends(get_db)):
    """
    Puxa pedidos (SC5) por período.
    """
    try:
        dt_de, dt_ate = sync_service.validate_period(req.dtDe, req.dtAte)
        data = protheus.get_wsgetpedx("SC5", dt_de=dt_de, dt_ate=dt_ate)

        sync_service.store_raw(db, "SC5", {"period": {"dtDe": dt_de, "dtAte": dt_ate}, "response": data})
        sync_service.log_run(db, "SC5", "orders", "success", {"dtDe": dt_de, "dtAte": dt_ate})
        return data

    except ValueError as e:
        sync_service.log_run(db, "SC5", "orders", "error", {"error": str(e)})
        raise HTTPException(status_code=400, detail=str(e)) from e

    except httpx.HTTPError as e:
        sync_service.log_run(db, "SC5", "orders", "error", {"error": str(e)})
        raise HTTPException(status_code=502, detail=str(e)) from e


@app.post("/sync/pull/invoices", dependencies=[Depends(require_api_key)])
def sync_invoices(req: PeriodRequest, db: Session = Depends(get_db)):
    """
    Puxa faturas (SF2) por período.
    """
    try:
        dt_de, dt_ate = sync_service.validate_period(req.dtDe, req.dtAte)
        data = protheus.get_wsgetpedx("SF2", dt_de=dt_de, dt_ate=dt_ate)

        sync_service.store_raw(db, "SF2", {"period": {"dtDe": dt_de, "dtAte": dt_ate}, "response": data})
        sync_service.log_run(db, "SF2", "invoices", "success", {"dtDe": dt_de, "dtAte": dt_ate})
        return data

    except ValueError as e:
        sync_service.log_run(db, "SF2", "invoices", "error", {"error": str(e)})
        raise HTTPException(status_code=400, detail=str(e)) from e

    except httpx.HTTPError as e:
        sync_service.log_run(db, "SF2", "invoices", "error", {"error": str(e)})
        raise HTTPException(status_code=502, detail=str(e)) from e


@app.post("/customers", dependencies=[Depends(require_api_key)])
def create_customer(body: CustomerBody, db: Session = Depends(get_db)):
    """
    Envia cliente para o Protheus:
    - POST /rest/WSCUSTOMERS
    Idempotência: A1_CPEDX (preferência) ou A1_CGC.
    """
    try:
        if not body.CLIENTES:
            raise ValueError("CLIENTES vazio.")

        c = body.CLIENTES[0]
        idem_key = str(c.get("A1_CPEDX") or c.get("A1_CGC") or "").strip()
        if not idem_key:
            raise ValueError("Cliente sem chave (faltou A1_CPEDX ou A1_CGC).")

        endpoint = "POST:/customers"
        existing = get_idem(db, idem_key, endpoint)
        if existing:
            return {"idempotent": True, "cached_response": existing.response_json}

        data = protheus.post_customers(body.model_dump(), altera=False)

        aRetUsr = None
        try:
            aRetUsr = data[0].get("aRetUsr", [None])[0]
        except Exception:
            aRetUsr = None

        if aRetUsr:
            a1_cod = str(aRetUsr.get("A1_COD", "")).strip()
            a1_loja = str(aRetUsr.get("A1_LOJA", "")).strip()
            cgc = str(aRetUsr.get("CGC", "")).strip()
            source_id = str(c.get("A1_CPEDX") or cgc).strip()

            upsert_mapping_customer(
                db,
                source_id=source_id,
                a1_cod=a1_cod,
                a1_loja=a1_loja,
                cgc=cgc,
                extra={"Mensagem": aRetUsr.get("Mensagem", "")},
            )

        save_idem(db, idem_key, endpoint, data)
        return data

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@app.put("/customers", dependencies=[Depends(require_api_key)])
def update_customer(body: CustomerBody, db: Session = Depends(get_db)):
    """
    Atualiza cliente no Protheus:
    - POST /rest/WSCUSTOMERS?cAltera=S
    Idempotência: A1_CPEDX (preferência) ou A1_CGC.
    """
    try:
        if not body.CLIENTES:
            raise ValueError("CLIENTES vazio.")

        c = body.CLIENTES[0]
        idem_key = str(c.get("A1_CPEDX") or c.get("A1_CGC") or "").strip()
        if not idem_key:
            raise ValueError("Cliente sem chave (faltou A1_CPEDX ou A1_CGC).")

        endpoint = "PUT:/customers"
        existing = get_idem(db, idem_key, endpoint)
        if existing:
            return {"idempotent": True, "cached_response": existing.response_json}

        data = protheus.post_customers(body.model_dump(), altera=True)

        aRetUsr = None
        try:
            aRetUsr = data[0].get("aRetUsr", [None])[0]
        except Exception:
            aRetUsr = None

        if aRetUsr:
            a1_cod = str(aRetUsr.get("A1_COD", "")).strip()
            a1_loja = str(aRetUsr.get("A1_LOJA", "")).strip()
            cgc = str(aRetUsr.get("CGC", "")).strip()
            source_id = str(c.get("A1_CPEDX") or cgc).strip()

            upsert_mapping_customer(
                db,
                source_id=source_id,
                a1_cod=a1_cod,
                a1_loja=a1_loja,
                cgc=cgc,
                extra={"Mensagem": aRetUsr.get("Mensagem", "")},
            )

        save_idem(db, idem_key, endpoint, data)
        return data

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@app.post("/salesorders", dependencies=[Depends(require_api_key)])
def create_salesorder(body: SalesOrderBody, db: Session = Depends(get_db)):
    """
    Envia pedido para o Protheus:
    - POST /rest/WSSALESORDERS

    Aplica defaults do documento:
    - C5_BIEFPGA = 'BOL'
    - C5_TIPO    = 'N'
    - C5_NATUREZ = '2001'
    - C6_LOCAL   = '13' nos itens

    Idempotência: C5_NUMEXT (preferência), ou C5_BIEPRE, ou C5_CPEDX.
    """
    try:
        if not body.PEDIDOS:
            raise ValueError("PEDIDOS vazio.")

        order_in = body.PEDIDOS[0]
        order = apply_order_defaults(order_in)
        idem_key = build_idempotency_key(order)

        cached = find_idem(db, idem_key)
        if cached:
            return {"idempotent": True, "cached_response": cached.response_json}

        payload = {"PEDIDOS": [order]}
        data = protheus.post_salesorders(payload)

        aRetUsr = None
        try:
            aRetUsr = data[0].get("aRetUsr", [None])[0]
        except Exception:
            aRetUsr = None

        if aRetUsr:
            c5_cpedx = str(aRetUsr.get("C5_CPEDX", "")).strip()
            c5_num = str(aRetUsr.get("C5_NUM", "")).strip()
            if c5_cpedx:
                upsert_mapping_order(
                    db,
                    source_id=c5_cpedx,
                    c5_num=c5_num,
                    extra={"Mensagem": aRetUsr.get("Mensagem", "")},
                )

        save_idem_order(db, idem_key, data)
        return data

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
