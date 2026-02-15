from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx


@dataclass(frozen=True)
class ProtheusConfig:
    base_url: str
    username: str
    password: str
    timeout_s: float = 30.0


class ProtheusClient:
    """
    Client para:
    - GET  /rest/WSGETPEDX
    - POST /rest/WSCUSTOMERS
    - POST /rest/WSSALESORDERS
    """

    def __init__(self, cfg: ProtheusConfig) -> None:
        self._client = httpx.Client(
            base_url=cfg.base_url.rstrip("/"),
            auth=(cfg.username, cfg.password),
            timeout=cfg.timeout_s,
        )

    def get_wsgetpedx(
        self,
        tabela: str,
        *,
        reset: bool = False,
        campo: Optional[str] = None,
        valor: Optional[str] = None,
        dt_de: Optional[str] = None,
        dt_ate: Optional[str] = None,
    ) -> Any:
        params: Dict[str, str] = {"cTabela": tabela}

        if reset:
            params["cReset"] = "S"

        if campo and valor:
            params["cCampo"] = campo
            params["cValor"] = valor

        if dt_de and dt_ate:
            params["cDtDe"] = dt_de
            params["cDtAte"] = dt_ate

        r = self._client.get("/rest/WSGETPEDX", params=params)
        r.raise_for_status()
        return r.json()

    def post_customers(self, payload: dict, *, altera: bool = False) -> Any:
        params = {"cAltera": "S"} if altera else None
        r = self._client.post("/rest/WSCUSTOMERS", params=params, json=payload)
        r.raise_for_status()
        return r.json()

    def post_salesorders(self, payload: dict) -> Any:
        r = self._client.post("/rest/WSSALESORDERS", json=payload)
        r.raise_for_status()
        return r.json()
