#!/usr/bin/env python3
"""Chamadas à Apify, portadas do ODI Atlas (collect_meta_apify.py e collect_meta_anuncios_apify.py).

Diferença deliberada: aqui NÃO existe consulta de saldo nem de limites da conta (/users/me/limits). O gasto é
controlado por dois freios que não dependem dela: o teto de cada execução (maxTotalChargeUsd) e a soma dos custos
gravados nos manifestos. O token vem só de variável de ambiente e nunca é gravado nem impresso.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

API = "https://api.apify.com/v2"


def api(method: str, path: str, token: str, body=None, timeout: int = 360):
    req = urllib.request.Request(f"{API}{path}", method=method,
                                 data=None if body is None else json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        # motivo informado pela Apify (tipo e mensagem; nunca contém o token), para diagnosticar 401/402/403
        try:
            err = (json.loads(e.read() or b"{}") or {}).get("error") or {}
            print(f"Apify HTTP {e.code}: {err.get('type')}: {str(err.get('message'))[:160]}", file=sys.stderr)
            e.msg = f"{e.msg} [{err.get('type')}]"
        except Exception:  # noqa: BLE001
            pass
        raise


def run_actor(token: str, actor: str, payload: dict, cap: float):
    """Roda o ator com teto de cobrança `cap` (US$) e devolve (execução, itens)."""
    run = api("POST", f"/acts/{actor}/runs?waitForFinish=300&maxTotalChargeUsd={cap}", token, payload)["data"]
    while run.get("status") in ("READY", "RUNNING"):
        run = api("GET", f"/actor-runs/{run['id']}?waitForFinish=300", token)["data"]
    items = api("GET", f"/datasets/{run['defaultDatasetId']}/items?clean=true&format=json", token) or []
    return run, items


def custo_run(run: dict) -> float:
    """Custo cobrado: eventos cobrados × preço do evento (faixa FREE quando há faixas); senão usageTotalUsd."""
    ev = ((run.get("pricingInfo") or {}).get("pricingPerEvent") or {}).get("actorChargeEvents") or {}
    tot = 0.0
    for nome, n in (run.get("chargedEventCounts") or {}).items():
        e = ev.get(nome) or {}
        preco = e.get("eventPriceUsd")
        if preco is None:
            preco = ((e.get("eventTieredPricingUsd") or {}).get("FREE") or {}).get("tieredEventPriceUsd") or 0
        tot += float(n or 0) * float(preco or 0)
    return round(tot or float(run.get("usageTotalUsd") or 0), 4)


def erro_curto(e: Exception) -> str:
    """Descrição do erro sem cabeçalhos nem token."""
    return f"{type(e).__name__} {getattr(e, 'code', '')} {getattr(e, 'msg', '') if getattr(e, 'code', None) else ''}".strip()[:160]
