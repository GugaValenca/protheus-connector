from sqlalchemy import String, DateTime, Integer, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from .db import Base


class SyncRun(Base):
    __tablename__ = "sync_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    table_name: Mapped[str] = mapped_column(String(10), index=True)
    mode: Mapped[str] = mapped_column(String(30))  # reset|pull|pull_filter|orders|invoices
    status: Mapped[str] = mapped_column(String(20))  # success|error
    details: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
    )


class ExternalMapping(Base):
    """
    Guarda vínculo entre IDs do sistema de origem (source_id) e IDs do Protheus.

    - customer: source_id (A1_CPEDX ou A1_CGC) -> (A1_COD, A1_LOJA)
    - order:    source_id (C5_CPEDX)          -> (C5_NUM)
    """
    __tablename__ = "external_mappings"
    __table_args__ = (UniqueConstraint("entity_type", "source_id", name="uq_entity_source"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(20), index=True)  # customer|order
    source_id: Mapped[str] = mapped_column(String(60), index=True)
    protheus_code: Mapped[str] = mapped_column(String(60), default="")
    protheus_store: Mapped[str] = mapped_column(String(10), default="")
    extra: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
    )


class IdempotencyKey(Base):
    """
    Evita duplicar POST/PUT (principalmente pedido e cliente).
    """
    __tablename__ = "idempotency_keys"
    __table_args__ = (UniqueConstraint("key", "endpoint", name="uq_key_endpoint"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(120), index=True)
    endpoint: Mapped[str] = mapped_column(String(80), index=True)
    response_json: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
    )


class RawStore(Base):
    """
    Guarda payload cru do Protheus (auditoria/debug).
    """
    __tablename__ = "raw_store"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    table_name: Mapped[str] = mapped_column(String(10), index=True)
    payload: Mapped[dict] = mapped_column(JSON)

    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
    )
