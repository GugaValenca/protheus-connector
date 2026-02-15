from sqlalchemy.orm import Session

from ..models import SyncRun, RawStore
from ..utils import yyyymmdd_or_raise


# Tabelas citadas no documento (inclui SA2 pois aparece no reset de fornecedores)
ALLOWED_TABLES = {"SA1", "SA2", "SA3",
                  "SA4", "SB1", "DA1", "SE4", "SC5", "SF2"}


def ensure_table(table: str) -> str:
    t = (table or "").strip().upper()
    if t not in ALLOWED_TABLES:
        raise ValueError(f"Tabela inválida: {table}")
    return t


def log_run(db: Session, table_name: str, mode: str, status: str, details: dict):
    run = SyncRun(table_name=table_name, mode=mode,
                  status=status, details=details)
    db.add(run)
    db.commit()
    return run.id


def store_raw(db: Session, table_name: str, payload: dict):
    db.add(RawStore(table_name=table_name, payload=payload))
    db.commit()


def validate_period(dt_de: str, dt_ate: str):
    return yyyymmdd_or_raise(dt_de), yyyymmdd_or_raise(dt_ate)
