#!/usr/bin/env python3
"""Biblioteca de Anúncios da Meta pela Apify (ator jmlp/meta-ad-library-scraper) — alternativa ao token oficial.

Cópia de scripts/collect_meta_anuncios_apify.py do ODI Atlas (mesmo método), com país, tipo de anúncio e segredo vindos de
data/config/meta_anuncios.json. Token SOMENTE pelo segredo da configuração (APIFY_TOKEN_ESP). Cada execução tem teto de gasto (maxTotalChargeUsd da Apify): --teste usa o teto de teste;
sem a opção, o teto diário. Também respeita o teto mensal somando os manifestos do mês.
Saídas: data/meta/anuncios.json (mesmo formato da coleta oficial; agregados), data/meta/manifesto-AAAA-MM-*.json (custo) e,
com ODI_INTERNO_DIR, meta/anuncios/apify_AAAA-MM-DD.jsonl.gz (bruto, privado).
"""
from __future__ import annotations

import datetime as dt
import gzip
import json
import os
import re
import sys
import unicodedata
import urllib.parse
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from meta_agregar import agregar  # noqa: E402
from apify import api, execucao_anterior, run_actor  # noqa: E402,F401
from net import now_utc  # noqa: E402


def faixa_de(v) -> dict | None:
    """Gasto/alcance em qualquer formato do ator → {'lower_bound','upper_bound'} (strings numéricas), ou None."""
    if v is None or v == "":
        return None
    if isinstance(v, dict):
        lo = v.get("lower_bound", v.get("lowerBound", v.get("min")))
        up = v.get("upper_bound", v.get("upperBound", v.get("max")))
        if lo is None and up is None:
            return None
        return {"lower_bound": str(lo or 0), "upper_bound": "" if up in (None, "") else str(up)}
    if isinstance(v, (int, float)):
        return {"lower_bound": str(int(v)), "upper_bound": str(int(v))}
    s = str(v)
    mult = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000, "MIL": 1_000, "MI": 1_000_000}

    def num(tok: str, suf: str) -> int:
        suf = suf.upper()
        if suf in mult:  # "1.5K" → 1500 (ponto decimal); "1,5 mil" → 1500
            return int(round(float(tok.replace(",", ".")) * mult[suf]))
        return int(tok.replace(".", "").replace(",", ""))
    nums = [num(t, u) for t, u in re.findall(r"(\d[\d.,]*)\s*(K|M|B|mil|mi)?\b", s, re.I)]
    if not nums:
        return None
    if s.strip().startswith("<"):
        return {"lower_bound": "0", "upper_bound": str(nums[0])}
    if len(nums) == 1:
        return {"lower_bound": str(nums[0]), "upper_bound": "" if ">" in s or "+" in s else str(nums[0])}
    return {"lower_bound": str(nums[0]), "upper_bound": str(nums[1])}


def iso(t) -> str:
    try:
        return dt.datetime.fromtimestamp(int(t), dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        return str(t or "")


def dominio(s: str) -> str:
    """Domínio de destino exibido no anúncio (sem caminho e sem www)."""
    s = str(s or "").strip().lower()
    s = urllib.parse.urlparse(s).netloc if "://" in s else s.split("/")[0]
    return s.removeprefix("www.")


def normalizar(x: dict) -> dict:
    snap = x.get("snapshot") or {}
    plat = x.get("publisher_platform") or x.get("publisher_platforms") or []
    if isinstance(plat, str):
        plat = [p.strip().lower() for p in plat.split(",") if p.strip()]
    return {"id": str(x.get("ad_archive_id") or x.get("adArchiveID") or x.get("id") or ""),
            "page_id": str(x.get("page_id") or snap.get("page_id") or ""), "page_name": x.get("page_name") or snap.get("page_name") or "",
            "bylines": snap.get("byline") or x.get("byline") or x.get("bylines") or "",
            "ad_delivery_start_time": iso(x.get("start_date") or x.get("startDate")),
            "ad_delivery_stop_time": iso(x.get("end_date") or x.get("endDate")),
            "spend": faixa_de(x.get("spend")),
            "impressions": faixa_de((x.get("impressions_with_index") or {}).get("impressions_text") if isinstance(x.get("impressions_with_index"), dict) else x.get("impressions")),
            "reach": faixa_de(x.get("reach_estimate") or x.get("reach")), "currency": x.get("currency") or "",
            "publisher_platforms": [str(p).lower() for p in plat], "delivery_by_region": x.get("delivery_by_region") or [],
            # a Meta classifica e, na UE (onde não aceita anúncio político desde 06/10/2025), retira: categories=POLITICAL, gated_type=TAKEN_DOWN
            "politico": "POLITICAL" in [str(c) for c in (x.get("categories") or [])], "retirado": x.get("gated_type") == "TAKEN_DOWN",
            "destino": dominio(snap.get("caption") or snap.get("link_url") or "")}


def textos_de(o) -> list[str]:
    if isinstance(o, str):
        return [o]
    if isinstance(o, dict):
        return [t for v in o.values() for t in textos_de(v)]
    if isinstance(o, list):
        return [t for v in o for t in textos_de(v)]
    return []


def _norm(s: str) -> str:
    return " ".join(unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower().split())


def cita(x: dict, termo: str) -> bool:
    """O nome aparece como FRASE no anúncio ou no nome da página? A busca da Biblioteca casa as palavras soltas, em
    qualquer ordem ('Foro Madrid' traz todo anúncio com 'foro' e 'Madrid'); esta marca separa o que cita o ator de fato."""
    return _norm(termo) in _norm(" \n ".join(textos_de(x.get("snapshot")) + [str(x.get("page_name") or "")]))


def do_privado(interno: str, ator: str, token: str = "") -> dict:
    """Execuções deste ator já guardadas no repositório privado por recuperar_bruto.py: {termo buscado (normalizado) → (execução, itens)}.
    O termo vem do endereço da Biblioteca que o ator devolve no campo `input` de cada item. Não inicia execução nenhuma."""
    base = Path(interno) / "apify_execucoes" / ator if interno else None
    if not base or not base.exists():
        return {}
    indice = json.loads((base.parent / "indice.json").read_text(encoding="utf-8")) if (base.parent / "indice.json").exists() else {}
    out = {}
    for f in sorted(base.glob("*.jsonl.gz"), key=lambda f: (indice.get(f.name.split(".")[0]) or {}).get("iniciada_em") or ""):
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            itens = [json.loads(ln) for ln in fh if ln.strip()]
        rid = f.name.split(".")[0]
        entrada = urllib.parse.unquote_plus(urllib.parse.unquote_plus(json.dumps([x.get("input") for x in itens[:3]], ensure_ascii=False)))
        m = re.search(r'[?&]q=([^&"\\]+)', entrada)
        if not m:
            print(f"execução {rid}: {len(itens)} itens, termo buscado não identificado (campo input: {type((itens or [{}])[0].get('input')).__name__})")
            continue
        run = {"id": rid, "status": (indice.get(rid) or {}).get("status") or "guardada no privado"}
        if token:
            try:
                run = api("GET", f"/actor-runs/{rid}", token)["data"]
            except Exception:  # noqa: BLE001
                pass
        out[_norm(m.group(1))] = (run, itens)  # a mais recente de cada termo prevalece
    return out


COLS = ["id", "consulta", "page_id", "page_name", "bylines", "ad_delivery_start_time", "ad_delivery_stop_time", "gasto_min", "gasto_max",
        "impressoes_min", "impressoes_max", "publico_estimado_min", "publico_estimado_max", "plataformas", "frase_exata", "politico", "retirado", "moeda", "destino", "visto_em"]
# publico_estimado = "estimated audience size" da Biblioteca (tamanho do público-alvo, ex.: ">1M"); NÃO é alcance nem impressões.


def linha(a: dict, consulta: str, agora: str) -> dict:
    g, i, r = a.get("spend") or {}, a.get("impressions") or {}, a.get("reach") or {}
    return {"id": a["id"], "consulta": consulta, "page_id": a["page_id"], "page_name": a["page_name"], "bylines": a["bylines"],
            "ad_delivery_start_time": a["ad_delivery_start_time"], "ad_delivery_stop_time": a["ad_delivery_stop_time"],
            "gasto_min": g.get("lower_bound", ""), "gasto_max": g.get("upper_bound", ""), "impressoes_min": i.get("lower_bound", ""),
            "impressoes_max": i.get("upper_bound", ""), "publico_estimado_min": r.get("lower_bound", ""), "publico_estimado_max": r.get("upper_bound", ""),
            "plataformas": ",".join(a["publisher_platforms"]), "frase_exata": {True: "1", False: "0"}.get(a.get("frase_exata"), ""), "politico": "1" if a.get("politico") else "0",
            "retirado": "1" if a.get("retirado") else "0", "moeda": a.get("currency") or "", "destino": a.get("destino") or "", "visto_em": agora}


def de_linha(r: dict) -> dict:
    f = lambda lo, up: {"lower_bound": r[lo] or "0", "upper_bound": r[up]} if (r[lo] or r[up]) else None  # noqa: E731
    return {"id": r["id"], "page_id": r["page_id"], "page_name": r["page_name"], "bylines": r["bylines"],
            "ad_delivery_start_time": r["ad_delivery_start_time"], "ad_delivery_stop_time": r["ad_delivery_stop_time"],
            "spend": f("gasto_min", "gasto_max"), "impressions": f("impressoes_min", "impressoes_max"),
            "currency": r.get("moeda") or "EUR", "publisher_platforms": [p for p in r["plataformas"].split(",") if p], "delivery_by_region": []}


TIPO = "all"  # na UE a Meta não aceita anúncios políticos desde 06/10/2025: a busca é em todos os anúncios (ad_type=all)


def url_biblioteca(termo: str, pais: str, desde: str) -> str:
    q = {"active_status": "all", "ad_type": TIPO, "country": pais, "q": termo,
         "search_type": "keyword_unordered", "media_type": "all", "start_date[min]": desde}
    return "https://www.facebook.com/ads/library/?" + urllib.parse.urlencode(q)


def custo_run(run: dict) -> float:
    """Custo cobrado: eventos cobrados × preço do evento (plano FREE quando há faixas); senão usageTotalUsd."""
    ev = ((run.get("pricingInfo") or {}).get("pricingPerEvent") or {}).get("actorChargeEvents") or {}
    tot = 0.0
    for nome, n in (run.get("chargedEventCounts") or {}).items():
        e = ev.get(nome) or {}
        preco = e.get("eventPriceUsd")
        if preco is None:
            preco = ((e.get("eventTieredPricingUsd") or {}).get("FREE") or {}).get("tieredEventPriceUsd") or 0
        tot += float(n or 0) * float(preco or 0)
    return round(tot or float(run.get("usageTotalUsd") or 0), 4)


def gasto_mes(pasta: Path) -> float:
    mes = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m")
    tot = 0.0
    for f in pasta.glob(f"manifesto-{mes}-*.json"):
        try:
            tot += float(json.loads(f.read_text(encoding="utf-8")).get("custo_usd") or 0)
        except Exception:  # noqa: BLE001
            pass
    return round(tot, 4)


def main(argv=None, executar=None) -> int:
    argv = list(argv or [])
    root = Path(".")
    cfg = json.loads((root / "data/config/meta_anuncios.json").read_text(encoding="utf-8"))
    recuperar = "--recuperar" in argv  # relê execuções JÁ PAGAS com o mesmo pedido; nunca inicia execução nova (sem custo)
    teste = "--teste" in argv or recuperar
    pasta = root / "data/meta"
    pasta.mkdir(parents=True, exist_ok=True)
    fases = json.loads((root / "data/config/temas.json").read_text(encoding="utf-8")).get("fases", [])
    global TIPO
    TIPO = cfg.get("ad_type", "all")
    agora = now_utc()
    teto = cfg["teto_teste_usd"] if teste else cfg["teto_diario_usd"]
    ja = gasto_mes(pasta)
    out = {"schema_version": 1, "coletado_em_utc": agora, "fonte": f"Meta · Biblioteca de Anúncios via Apify ({cfg['ator'].replace('~', '/')})",
           "nota": cfg["nota"], "desde": cfg["desde"], "consultas": {}, "erros": {}, "modo": "recuperação" if recuperar else ("teste" if teste else "diário"),
           "teto_usd": teto, "gasto_mes_antes_usd": ja}
    token = os.environ.get(cfg.get("segredo", "APIFY_TOKEN_ESP"), "").strip()
    if not token and executar is None:
        out["status"] = "⛔ segredo da Apify ausente"
    elif not recuperar and ja + teto > cfg["teto_mensal_usd"] + 1e-9:
        out["status"] = f"⛔ teto mensal de US$ {cfg['teto_mensal_usd']} atingido (já gasto US$ {ja})"
    if "status" in out:
        (pasta / "anuncios.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        print(out["status"])
        return 1
    if recuperar and executar is None:
        corte = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=6)).strftime("%Y-%m-%dT%H:%M:%S")

        guardadas = do_privado(os.environ.get("ATLAS_INTERNO_DIR") or os.environ.get("ODI_INTERNO_DIR") or "", cfg["ator"], token)
        print("execuções guardadas no privado, por termo buscado: " + (", ".join(f"{t} ({len(i)} itens)" for t, (_, i) in guardadas.items()) or "nenhuma"))

        def executar(payload, cap):
            termo = urllib.parse.parse_qs(urllib.parse.urlparse(payload["adLibraryUrls"][0]).query).get("q", [""])[0]
            ant = guardadas.get(_norm(termo)) or execucao_anterior(token, cfg["ator"], payload, corte)
            if not ant:
                raise LookupError("sem execução anterior com este pedido")
            return ant
    executar = executar or (lambda payload, cap: run_actor(token, cfg["ator"], payload, cap))
    pagas = set()  # execuções já registradas em manifestos anteriores: o custo delas não é somado de novo
    for f in pasta.glob("manifesto-*.json"):
        try:
            pagas |= {r.get("id") for r in json.loads(f.read_text(encoding="utf-8")).get("runs") or []}
        except Exception:  # noqa: BLE001
            pass
    max_ads = cfg["max_anuncios_por_consulta_teste" if teste else "max_anuncios_por_consulta_diario"]
    # teste: anúncios com exibição desde o início do período; diário: com exibição desde ontem (os maiores primeiro)
    janela = cfg["desde"] if teste else (dt.date.fromisoformat(agora[:10]) - dt.timedelta(days=1)).isoformat()
    custo, brutos, runs = 0.0, [], []
    novos = {}
    cap = round(teto / len(cfg["consultas"]), 4)
    for c in cfg["consultas"]:  # uma execução por consulta: a origem de cada anúncio fica certa
        payload = {"adLibraryUrls": [url_biblioteca(c["termo"], cfg["pais"], janela)], "country": cfg["pais"],
                   "minDate": janela, "maxAds": max_ads, "activeStatus": "all"}
        try:
            run, itens = executar(payload, cap)
            c_run = 0.0 if run.get("id") in pagas else custo_run(run)
            custo += c_run
            runs.append({"consulta": c["id"], "id": run.get("id"), "status": run.get("status"), "custo_usd": c_run, "ja_registrada": run.get("id") in pagas, "itens": len(itens or [])})
            for x in itens or []:
                brutos.append({"_consulta": c["id"], **x})
                a_ = normalizar(x)
                a_["frase_exata"] = cita(x, c["termo"])
                if a_["id"]:
                    novos[(c["id"], a_["id"])] = linha(a_, c["id"], agora)
        except Exception as e:  # noqa: BLE001 — o token vai no cabeçalho, não na mensagem
            out["erros"][c["id"]] = f"{type(e).__name__} {getattr(e, 'code', '')}".strip()
            feita = getattr(e, "run", None)
            if feita:  # a execução aconteceu e pode ter sido cobrada: o custo entra no manifesto mesmo sem os itens
                custo += custo_run(feita)
                runs.append({"consulta": c["id"], "id": feita.get("id"), "status": "feita, resultado não baixado", "custo_usd": custo_run(feita), "itens": None})
    out["runs_apify"] = runs
    # acumulado público (sem texto dos anúncios): última leitura de cada anúncio por consulta
    hist = pasta / "anuncios_apify.csv"
    acum = {}
    if hist.exists():
        import csv as _csv
        acum = {(r["consulta"], r["id"]): {**{k: r.get(k, "") for k in COLS}, "publico_estimado_min": r.get("publico_estimado_min") or r.get("alcance_min", ""),
                                              "publico_estimado_max": r.get("publico_estimado_max") or r.get("alcance_max", "")}
                for r in _csv.DictReader(open(hist, encoding="utf-8"), delimiter=";")}
    acum.update(novos)
    import csv as _csv
    with open(hist, "w", encoding="utf-8", newline="") as f:
        w = _csv.DictWriter(f, COLS, delimiter=";", lineterminator="\n")
        w.writeheader()
        w.writerows(sorted(acum.values(), key=lambda r: (r["consulta"], r["id"])))
    for c in cfg["consultas"]:
        ads = [de_linha(r) for (q, _), r in acum.items() if q == c["id"]]
        hoje = sum(1 for (q, _) in novos if q == c["id"])
        marcas = [r for (q, _), r in acum.items() if q == c["id"]]
        exatas = [r for r in marcas if r.get("frase_exata") == "1"]
        marcado = all(r.get("frase_exata") in ("0", "1") for r in marcas)
        pol, por_moeda = [r for r in marcas if r.get("politico") == "1"], {}
        for r in pol:  # gasto é faixa informada pela Meta, na moeda do anunciante: nunca somar moedas diferentes
            m = por_moeda.setdefault(r.get("moeda") or "?", {"anuncios": 0, "gasto_min": 0, "gasto_max": 0})
            m["anuncios"], m["gasto_min"], m["gasto_max"] = m["anuncios"] + 1, m["gasto_min"] + int(r["gasto_min"] or 0), m["gasto_max"] + int(r["gasto_max"] or 0)
        out["consultas"][c["id"]] = {"ator": c["ator"], "termo": c["termo"], "paginas_api": None, "com_frase_exata": len(exatas) if marcado else None,
                                     "paginas_com_frase_exata": Counter(r["page_name"] for r in exatas).most_common(15),
                                     "frase_exata_paginas_distintas": len({r["page_id"] for r in exatas}), "frase_exata_por_mes_de_inicio": dict(sorted(Counter(r["ad_delivery_start_time"][:7] for r in exatas if r["ad_delivery_start_time"]).items())),
                                     "destinos_frase_exata": Counter(r.get("destino") or "(sem destino)" for r in exatas).most_common(15),
                                     "classificados_politicos": len(pol), "politicos_retirados_pela_meta": sum(1 for r in pol if r.get("retirado") == "1"),
                                     "politicos_iniciados_no_periodo": sum(1 for r in pol if r["ad_delivery_start_time"][:10] >= cfg["desde"]),
                                     "paginas_dos_politicos": Counter(r["page_name"] for r in pol).most_common(15), "gasto_por_moeda": por_moeda, "lidos_nesta_execucao": hoje,
                                     "limite_da_coleta": max_ads, "no_limite": hoje >= max_ads, **agregar(ads, fases)}
        print(f"{c['ator']} ({c['termo']}): classificados como políticos pela Meta {len(pol)} (retirados {sum(1 for r in pol if r.get('retirado') == '1')}) · com o nome como frase exata {len(exatas) if marcado else '⛔ não marcado'} · {hoje} lidos nesta execução{' (limite atingido)' if hoje >= max_ads else ''}; {len(ads)} no acumulado")
    ok = any(v["anuncios"] for v in out["consultas"].values())
    out["janela_desta_execucao"] = janela
    out["status"] = "ok" if ok and not out["erros"] else ("⚠️ parcial" if ok else "⛔ " + ("; ".join(f"{k}: {v}" for k, v in out["erros"].items()) or "nenhum anúncio"))
    out["custo_usd"] = custo
    out["nota_campos"] = ("'gasto' de cada consulta soma faixas de moedas diferentes quando há mais de uma: use gasto_por_moeda. "
                          "publico_estimado é o tamanho do público-alvo informado pela Biblioteca, não alcance. "
                          "Só anúncios que a Meta classificou como políticos trazem gasto e público estimado.")
    (pasta / "anuncios.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    (pasta / f"manifesto-{agora[:7]}-{agora.replace(':', '').replace('-', '')}.json").write_text(
        json.dumps({"coletado_em_utc": agora, "modo": out["modo"], "teto_usd": teto, "custo_usd": custo, "itens": len(brutos),
                    "runs": runs}, ensure_ascii=False, indent=1), encoding="utf-8")
    interno = os.environ.get("ATLAS_INTERNO_DIR") or os.environ.get("ODI_INTERNO_DIR")
    if interno and brutos and not recuperar:  # na recuperação o bruto já está no privado (apify_execucoes/)
        d = Path(interno) / "meta/anuncios"
        d.mkdir(parents=True, exist_ok=True)
        with gzip.open(d / f"apify_{agora[:10]}.jsonl.gz", "wt", encoding="utf-8") as f:
            for x in brutos:
                f.write(json.dumps(x, ensure_ascii=False) + "\n")
    print(f"meta via apify: {out['status']} · {len(brutos)} itens · custo US$ {custo} (teto {teto}) · mês antes US$ {ja}")
    if brutos:
        print("campos do 1º item: " + ", ".join(sorted(brutos[0].keys()))[:900])
        for k in ("reach_estimate", "spend", "impressions_with_index", "currency"):  # forma dos campos numéricos (sem texto de anúncio)
            v = next((x.get(k) for x in brutos if x.get(k) not in (None, "", [], {})), None)
            print(f"amostra do campo {k}: {json.dumps(v, ensure_ascii=False)[:200]} · preenchido em {sum(1 for x in brutos if x.get(k) not in (None, '', [], {}))} de {len(brutos)}")
        print("chaves de snapshot: " + ", ".join(sorted({k for x in brutos[:50] for k in (x.get('snapshot') or {})}))[:700])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
