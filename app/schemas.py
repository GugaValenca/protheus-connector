from pydantic import BaseModel, Field
from typing import Any, List, Dict


class PullRequest(BaseModel):
    table: str = Field(...,
                       description="SA1, SA3, SA4, SB1, DA1, SE4, SC5, SF2")
    reset: bool = False


class FilterRequest(BaseModel):
    table: str
    campo: str
    valor: str


class PeriodRequest(BaseModel):
    dtDe: str
    dtAte: str


class CustomerBody(BaseModel):
    CLIENTES: List[Dict[str, Any]]


class SalesOrderBody(BaseModel):
    PEDIDOS: List[Dict[str, Any]]
