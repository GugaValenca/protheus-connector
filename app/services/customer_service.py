from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ExternalMapping, IdempotencyKey


def get_idem(db: Session, key: str, endpoint: str) -> IdempotencyKey | None:
    stmt = select(IdempotencyKey).where(
        IdempotencyKey.key == key,
        IdempotencyKey.endpoint == endpoint,
    )
    return db.execute(stmt).scalar_one_or_none()


def save_idem(db: Session, key: str, endpoint: str, response_json: dict) -> IdempotencyKey:
    idem = IdempotencyKey(key=key, endpoint=endpoint,
                          response_json=response_json)
    db.add(idem)
    db.commit()
    return idem


def upsert_mapping_customer(
    db: Session,
    source_id: str,
    a1_cod: str,
    a1_loja: str,
    cgc: str,
    extra: dict | None = None,
) -> ExternalMapping:
    stmt = select(ExternalMapping).where(
        ExternalMapping.entity_type == "customer",
        ExternalMapping.source_id == source_id,
    )
    m = db.execute(stmt).scalar_one_or_none()

    new_extra = {**(m.extra or {}), **(extra or {}),
                 "CGC": cgc} if m else {**(extra or {}), "CGC": cgc}

    if m:
        m.protheus_code = a1_cod or m.protheus_code
        m.protheus_store = a1_loja or m.protheus_store
        m.extra = new_extra
    else:
        m = ExternalMapping(
            entity_type="customer",
            source_id=source_id,
            protheus_code=a1_cod or "",
            protheus_store=a1_loja or "",
            extra=new_extra,
        )
        db.add(m)

    db.commit()
    return m
