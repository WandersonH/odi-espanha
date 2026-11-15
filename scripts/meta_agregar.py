"""Agregação dos anúncios da Biblioteca da Meta: funções faixa, soma, fase_de e agregar copiadas de
scripts/collect_meta_anuncios.py do ODI Atlas (mesmo método). Gasto, impressões e alcance são faixas informadas pela Meta."""
from __future__ import annotations

from collections import defaultdict


def faixa(d: dict | None) -> tuple[int, int | None]:
    d = d or {}
    lo = int(d.get("lower_bound") or 0)
    up = d.get("upper_bound")
    return lo, (int(up) if up not in (None, "") else None)


def soma(faixas: list[tuple[int, int | None]]) -> dict:
    lo = sum(a for a, _ in faixas)
    abertos = sum(1 for _, b in faixas if b is None)
    return {"min": lo, "max": None if abertos else sum(b for _, b in faixas), "faixas_abertas": abertos}


def fase_de(data: str, fases: list[dict]) -> str | None:
    for f in fases:
        if f["de"] <= (data or "")[:10] <= f["ate"]:
            return f["id"]
    return None


def agregar(ads: list[dict], fases: list[dict]) -> dict:
    por_pag = defaultdict(list)
    for a in ads:
        por_pag[(a.get("page_id"), a.get("page_name"))].append(a)
    paginas = []
    for (pid, nome), xs in por_pag.items():
        g = soma([faixa(a.get("spend")) for a in xs])
        paginas.append({"page_id": pid, "pagina": nome, "anuncios": len(xs), "gasto": g,
                        "impressoes": soma([faixa(a.get("impressions")) for a in xs]),
                        "pagadores": sorted({a.get("bylines") for a in xs if a.get("bylines")})[:3]})
    paginas.sort(key=lambda p: (-p["gasto"]["min"], -p["anuncios"]))
    reg = defaultdict(float)
    for a in ads:
        lo, _ = faixa(a.get("spend"))
        for r in a.get("delivery_by_region") or []:
            reg[r.get("region")] += lo * float(r.get("percentage") or 0)
    plat = defaultdict(int)
    for a in ads:
        for p in a.get("publisher_platforms") or []:
            plat[p] += 1
    return {"anuncios": len(ads), "paginas": len(paginas), "gasto": soma([faixa(a.get("spend")) for a in ads]),
            "impressoes": soma([faixa(a.get("impressions")) for a in ads]),
            "moedas": sorted({a.get("currency") for a in ads if a.get("currency")}),
            "plataformas": dict(sorted(plat.items(), key=lambda x: -x[1])),
            "fases": [{"id": f["id"], "rotulo": f["rotulo"], "de": f["de"], "ate": f["ate"],
                       **(lambda xs: {"anuncios": len(xs), "gasto": soma([faixa(a.get("spend")) for a in xs])})(
                           [a for a in ads if fase_de(a.get("ad_delivery_start_time"), [f])])} for f in fases],
            # reconciliação: anúncios sem data de início ou com início fora das fases (antes de 20/07, ou ainda veiculando de antes)
            "fora_das_fases": (lambda xs: {"anuncios": len(xs), "sem_data": sum(1 for a in xs if not a.get("ad_delivery_start_time")),
                                           "gasto": soma([faixa(a.get("spend")) for a in xs])})(
                [a for a in ads if not fase_de(a.get("ad_delivery_start_time"), fases)]),
            "regioes_gasto_min_estimado": [{"regiao": k, "gasto_min": round(v)} for k, v in sorted(reg.items(), key=lambda x: -x[1])[:27]],
            "top_paginas": paginas[:25]}
