"""
API intermediária (FastAPI) para integrar com TOTVS Protheus via endpoints REST do documento:

- GET  /rest/WSGETPEDX
- POST /rest/WSCUSTOMERS
- POST /rest/WSSALESORDERS
"""

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query
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


# --- Infra (DB / Client) ------------------------------------------------------

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


# --- Util ---------------------------------------------------------------------

def _safe_first_aretusr(data):
    """
    Retorno esperado no documento costuma vir assim:
    data[0]["aRetUsr"][0]
    Mas pode variar; aqui a gente tenta e, se não bater, retorna None.
    """
    try:
        return data[0].get("aRetUsr", [None])[0]
    except (TypeError, KeyError, IndexError, AttributeError):
        return None


# --- Endpoints básicos ---------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "env": settings.APP_ENV}


@app.get("/meta/protheus", dependencies=[Depends(require_api_key)])
def meta_protheus():
    return {
        "wsgetpedx_tables": ["SA1", "SA3", "SA4", "SB1", "DA1", "SE4", "SC5", "SF2"],
        "customers": {"create": "/rest/WSCUSTOMERS", "update": "/rest/WSCUSTOMERS?cAltera=S"},
        "salesorders": {"create": "/rest/WSSALESORDERS"},
    }


# --- Rotas internas (conveniência) --------------------------------------------

@app.post("/sync/reset/{table}", dependencies=[Depends(require_api_key)])
def sync_reset(table: str, db: Session = Depends(get_db)):
    try:
        t = sync_service.ensure_table(table)
        data = protheus.get_wsgetpedx(t, reset=True)

        sync_service.store_raw(db, t, {"reset_response": data})
        sync_service.log_run(db, t, "reset", "success", {"response": data})
        return data

    except ValueError as e:
        sync_service.log_run(db, (table or "").upper(),
                             "reset", "error", {"error": str(e)})
        raise HTTPException(status_code=400, detail=str(e)) from e

    except httpx.HTTPError as e:
        sync_service.log_run(db, (table or "").upper(),
                             "reset", "error", {"error": str(e)})
        raise HTTPException(status_code=502, detail=str(e)) from e


@app.post("/sync/pull", dependencies=[Depends(require_api_key)])
def sync_pull(req: PullRequest, db: Session = Depends(get_db)):
    try:
        t = sync_service.ensure_table(req.table)
        data = protheus.get_wsgetpedx(t, reset=req.reset)

        sync_service.store_raw(db, t, {"pull_response": data})
        sync_service.log_run(db, t, "pull", "success", {"reset": req.reset})
        return data

    except ValueError as e:
        sync_service.log_run(db, (req.table or "").upper(),
                             "pull", "error", {"error": str(e)})
        raise HTTPException(status_code=400, detail=str(e)) from e

    except httpx.HTTPError as e:
        sync_service.log_run(db, (req.table or "").upper(),
                             "pull", "error", {"error": str(e)})
        raise HTTPException(status_code=502, detail=str(e)) from e


@app.post("/sync/pull/filter", dependencies=[Depends(require_api_key)])
def sync_pull_filter(req: FilterRequest, db: Session = Depends(get_db)):
    try:
        t = sync_service.ensure_table(req.table)
        if not req.campo.strip() or not req.valor.strip():
            raise ValueError("campo/valor não podem ser vazios.")

        data = protheus.get_wsgetpedx(
            t, campo=req.campo.strip(), valor=req.valor.strip())

        sync_service.store_raw(
            db, t, {"filter": {"campo": req.campo, "valor": req.valor}, "response": data})
        sync_service.log_run(db, t, "pull_filter", "success", {
                             "campo": req.campo, "valor": req.valor})
        return data

    except ValueError as e:
        sync_service.log_run(db, (req.table or "").upper(),
                             "pull_filter", "error", {"error": str(e)})
        raise HTTPException(status_code=400, detail=str(e)) from e

    except httpx.HTTPError as e:
        sync_service.log_run(db, (req.table or "").upper(),
                             "pull_filter", "error", {"error": str(e)})
        raise HTTPException(status_code=502, detail=str(e)) from e


@app.post("/sync/pull/orders", dependencies=[Depends(require_api_key)])
def sync_orders(req: PeriodRequest, db: Session = Depends(get_db)):
    try:
        dt_de, dt_ate = sync_service.validate_period(req.dtDe, req.dtAte)
        data = protheus.get_wsgetpedx("SC5", dt_de=dt_de, dt_ate=dt_ate)

        sync_service.store_raw(
            db, "SC5", {"period": {"dtDe": dt_de, "dtAte": dt_ate}, "response": data})
        sync_service.log_run(db, "SC5", "orders", "success", {
                             "dtDe": dt_de, "dtAte": dt_ate})
        return data

    except ValueError as e:
        sync_service.log_run(db, "SC5", "orders", "error", {"error": str(e)})
        raise HTTPException(status_code=400, detail=str(e)) from e

    except httpx.HTTPError as e:
        sync_service.log_run(db, "SC5", "orders", "error", {"error": str(e)})
        raise HTTPException(status_code=502, detail=str(e)) from e


@app.post("/sync/pull/invoices", dependencies=[Depends(require_api_key)])
def sync_invoices(req: PeriodRequest, db: Session = Depends(get_db)):
    try:
        dt_de, dt_ate = sync_service.validate_period(req.dtDe, req.dtAte)
        data = protheus.get_wsgetpedx("SF2", dt_de=dt_de, dt_ate=dt_ate)

        sync_service.store_raw(
            db, "SF2", {"period": {"dtDe": dt_de, "dtAte": dt_ate}, "response": data})
        sync_service.log_run(db, "SF2", "invoices", "success", {
                             "dtDe": dt_de, "dtAte": dt_ate})
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
    POST /rest/WSCUSTOMERS
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

        aRetUsr = _safe_first_aretusr(data)
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
    POST /rest/WSCUSTOMERS?cAltera=S
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

        aRetUsr = _safe_first_aretusr(data)
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
    POST /rest/WSSALESORDERS
    - aplica defaults do documento
    - idempotência por C5_NUMEXT (preferência), C5_BIEPRE, ou C5_CPEDX
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

        aRetUsr = _safe_first_aretusr(data)
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


# --- Rotas do documento (EXATAS) ----------------------------------------------

@app.get("/rest/WSGETPEDX", dependencies=[Depends(require_api_key)])
def rest_wsgetpedx(
    cTabela: str = Query(...,
                         description="Nome da tabela (SA1, SA3, SA4, SB1, DA1, SE4, SC5, SF2)"),
    cReset: str | None = Query(None, description="S para resetar cache"),
    cCampo: str | None = Query(None, description="Nome do campo para filtro"),
    cValor: str | None = Query(None, description="Valor do filtro"),
    cDtDe: str | None = Query(None, description="Data inicial (yyyymmdd)"),
    cDtAte: str | None = Query(None, description="Data final (yyyymmdd)"),
    db: Session = Depends(get_db),
):
    try:
        table = sync_service.ensure_table(cTabela)

        reset = (cReset or "").strip().upper() == "S"
        campo = (cCampo or "").strip() or None
        valor = (cValor or "").strip() or None
        dt_de = (cDtDe or "").strip() or None
        dt_ate = (cDtAte or "").strip() or None

        # valida período se vier completo
        if (dt_de and not dt_ate) or (dt_ate and not dt_de):
            raise ValueError(
                "Para consulta por período, envie cDtDe e cDtAte juntos.")
        if dt_de and dt_ate:
            dt_de, dt_ate = sync_service.validate_period(dt_de, dt_ate)

        data = protheus.get_wsgetpedx(
            table,
            reset=reset,
            campo=campo,
            valor=valor,
            dt_de=dt_de,
            dt_ate=dt_ate,
        )

        sync_service.store_raw(
            db,
            table,
            {
                "request": {
                    "cTabela": table,
                    "cReset": cReset,
                    "cCampo": cCampo,
                    "cValor": cValor,
                    "cDtDe": cDtDe,
                    "cDtAte": cDtAte,
                },
                "response": data,
            },
        )
        sync_service.log_run(
            db,
            table,
            "wsgetpedx",
            "success",
            {"cReset": reset, "cCampo": campo, "cValor": valor,
                "cDtDe": dt_de, "cDtAte": dt_ate},
        )

        return data

    except ValueError as e:
        sync_service.log_run(db, (cTabela or "").upper(),
                             "wsgetpedx", "error", {"error": str(e)})
        raise HTTPException(status_code=400, detail=str(e)) from e

    except httpx.HTTPError as e:
        sync_service.log_run(db, (cTabela or "").upper(),
                             "wsgetpedx", "error", {"error": str(e)})
        raise HTTPException(status_code=502, detail=str(e)) from e


@app.post("/rest/WSCUSTOMERS", dependencies=[Depends(require_api_key)])
def rest_wscustomers(
    body: CustomerBody,
    cAltera: str | None = Query(
        None, description="Quando cAltera=S, altera cliente existente"),
    db: Session = Depends(get_db),
):
    try:
        altera = (cAltera or "").strip().upper() == "S"
        if altera:
            return update_customer(body, db)  # type: ignore[arg-type]
        return create_customer(body, db)  # type: ignore[arg-type]

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@app.post("/rest/WSSALESORDERS", dependencies=[Depends(require_api_key)])
def rest_wssalesorders(body: SalesOrderBody, db: Session = Depends(get_db)):
    try:
        return create_salesorder(body, db)  # type: ignore[arg-type]

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
