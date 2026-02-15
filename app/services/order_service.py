from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import IdempotencyKey, ExternalMapping

ORDER_ENDPOINT = "POST:/salesorders"


def find_idem(db: Session, key: str) -> IdempotencyKey | None:
    stmt = select(IdempotencyKey).where(
        IdempotencyKey.key == key,
        IdempotencyKey.endpoint == ORDER_ENDPOINT,
    )
    return db.execute(stmt).scalar_one_or_none()


def save_idem(db: Session, key: str, response_json: dict) -> IdempotencyKey:
    idem = IdempotencyKey(key=key, endpoint=ORDER_ENDPOINT,
                          response_json=response_json)
    db.add(idem)
    db.commit()
    return idem


def upsert_mapping_order(db: Session, source_id: str, c5_num: str, extra: dict | None = None) -> ExternalMapping:
    stmt = select(ExternalMapping).where(
        ExternalMapping.entity_type == "order",
        ExternalMapping.source_id == source_id,
    )
    m = db.execute(stmt).scalar_one_or_none()

    new_extra = {**(m.extra or {}), **(extra or {})} if m else (extra or {})

    if m:
        m.protheus_code = c5_num or m.protheus_code
        m.extra = new_extra
    else:
        m = ExternalMapping(
            entity_type="order",
            source_id=source_id,
            protheus_code=c5_num or "",
            extra=new_extra,
        )
        db.add(m)

    db.commit()
    return m


def apply_order_defaults(order: dict) -> dict:
   
    o = dict(order)

    o.setdefault("C5_BIEFPGA", "BOL")
    o.setdefault("C5_TIPO", "N")
    o.setdefault("C5_NATUREZ", "2001")

    if isinstance(o.get("ITENS"), list):
        itens = []
        for it in o["ITENS"]:
            it2 = dict(it)
            it2.setdefault("C6_LOCAL", "13")
            itens.append(it2)
        o["ITENS"] = itens

    return o


def build_idempotency_key(order: dict) -> str:
    
    for k in ("C5_NUMEXT", "C5_BIEPRE", "C5_CPEDX"):
        v = str(order.get(k, "")).strip()
        if v:
            return v
    raise ValueError(
        "Pedido sem chave de idempotência (faltou C5_NUMEXT/C5_BIEPRE/C5_CPEDX).")
