"""Capa HTTP compartida: caché en disco, límite de velocidad por host y contador de llamadas.

Todo acceso a internet de LukAI pasa por `obtener()`. Así:
- ninguna URL se descarga dos veces mientras su caché esté vigente;
- se respeta el límite de cada fuente (SEC: 10 req/s; Alpha Vantage: cupo diario);
- queda registro de cuántas llamadas se hicieron hoy por fuente (data/cache/_llamadas.json).
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import threading
import time
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import requests

RAIZ = Path(__file__).resolve().parent.parent
CACHE = Path(os.environ.get("LUKAI_CACHE", RAIZ / "data" / "cache"))
USER_AGENT = os.environ.get("LUKAI_USER_AGENT", "LukAI investment research (personal use) lukai@example.com")

# Segundos mínimos entre llamadas al mismo host y cupo diario (None = sin cupo).
LIMITES = {
    "data.sec.gov": (0.12, None),
    "www.sec.gov": (0.12, None),
    "www.alphavantage.co": (1.0, int(os.environ.get("LUKAI_AV_CUPO", "25"))),
    "financialmodelingprep.com": (0.3, int(os.environ.get("LUKAI_FMP_CUPO", "250"))),
    "fred.stlouisfed.org": (0.2, None),
    "stooq.com": (0.5, None),
    "query1.finance.yahoo.com": (0.5, None),
}

_ultima: dict[str, float] = {}
_candado = threading.Lock()
estadisticas = {"red": 0, "cache": 0}


class CupoAgotado(RuntimeError):
    """El cupo diario de la fuente ya se usó; el llamador debe pasar a la ruta alterna."""


def _ruta_cache(url: str) -> Path:
    h = hashlib.sha1(url.encode()).hexdigest()
    host = urlparse(url).netloc.replace(":", "_")
    return CACHE / host / f"{h}.gz"


def _contador() -> dict:
    p = CACHE / "_llamadas.json"
    try:
        d = json.loads(p.read_text())
    except (OSError, ValueError):
        d = {}
    hoy = date.today().isoformat()
    if d.get("fecha") != hoy:
        d = {"fecha": hoy, "hosts": {}}
    return d


def _registrar(host: str) -> None:
    d = _contador()
    d["hosts"][host] = d["hosts"].get(host, 0) + 1
    p = CACHE / "_llamadas.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d))


def llamadas_hoy(host: str) -> int:
    return _contador()["hosts"].get(host, 0)


def obtener(url: str, ttl_horas: float, *, binario: bool = False, clave_cache: str | None = None,
            guardar: bool = True) -> str | bytes:
    """Descarga `url` respetando caché y límites.

    `clave_cache` excluye secretos (API keys) de la clave de caché.
    `guardar=False` no escribe la respuesta cruda en disco (para archivos grandes de los que solo se guarda un resumen).
    """
    ruta = _ruta_cache(clave_cache or url)
    if ruta.exists() and (time.time() - ruta.stat().st_mtime) < ttl_horas * 3600:
        estadisticas["cache"] += 1
        datos = gzip.decompress(ruta.read_bytes())
        return datos if binario else datos.decode()

    host = urlparse(url).netloc
    espera, cupo = LIMITES.get(host, (0.5, None))
    with _candado:  # respeta el límite por host aunque haya varios hilos
        if cupo is not None and llamadas_hoy(host) >= cupo:
            raise CupoAgotado(f"Cupo diario de {host} agotado ({cupo} llamadas)")
        transcurrido = time.time() - _ultima.get(host, 0)
        if transcurrido < espera:
            time.sleep(espera - transcurrido)
        _ultima[host] = time.time()
        _registrar(host)
        estadisticas["red"] += 1

    r = requests.get(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"}, timeout=60)
    r.raise_for_status()
    if guardar:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_bytes(gzip.compress(r.content))
    return r.content if binario else r.text


def obtener_json(url: str, ttl_horas: float, clave_cache: str | None = None, guardar: bool = True):
    return json.loads(obtener(url, ttl_horas, clave_cache=clave_cache, guardar=guardar))
