#!/usr/bin/env python3
"""Notícias e artigos publicados nos sites oficiais de data/config/sites.json, no período de data/config/projeto.json.

Sem Apify e sem custo. Os três sites são WordPress, então a leitura usa o que o próprio WordPress oferece ao público:
1. API pública (wp-json/wp/v2): descobre os tipos de conteúdo do site (posts e tipos próprios, como "artículos" ou
   "noticias"), lista cada um do mais recente para trás com o filtro de data e lê do cabeçalho X-WP-Total o UNIVERSO
   que o site informa: quantas publicações existem no total e quantas no período.
2. Se a API não responder, o RSS paginado (/feed/?paged=N), que traz título, data, seção e autor, mas não informa
   total (universo ⛔ desconhecido) e cobre só o tipo "post".

Boas maneiras: respeita o robots.txt, se identifica no User-Agent (net.UA), espera `intervalo_s` entre os pedidos.
Site que recusar a leitura fica ⛔ com o código HTTP, sem tentativa de contorno.

Público: data/sites/artigos.csv.gz (título, datas, tipo, seções, autor, endereço) e manifestos. Resumo e texto integral
são de autoria dos sites: só são pedidos quando há repositório privado (ATLAS_INTERNO_DIR) e ficam só lá, para o corpus.
"""
from __future__ import annotations

import csv
import email.utils
import gzip
import html
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.robotparser
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comum  # noqa: E402
from net import UA, now_utc, open_url, read_body  # noqa: E402

SCOLS = ["site_id", "ator_id", "tipo", "artigo_id", "url", "publicado_em", "modificado_em", "titulo", "categorias", "autor", "via",
         "primeira_coleta", "ultima_coleta"]
DC = "{http://purl.org/dc/elements/1.1/}creator"
CONTEUDO = "{http://purl.org/rss/1.0/modules/content/}encoded"


def http(url: str) -> tuple[int, dict, bytes]:
    """(código, cabeçalhos em minúsculas, corpo). Erro HTTP volta como código; erro de rede como 0."""
    try:
        with open_url(url, timeout=60, headers={"Accept": "application/json, application/rss+xml, text/xml, */*"}) as r:
            return r.status, {k.lower(): v for k, v in r.headers.items()}, read_body(r)
    except urllib.error.HTTPError as e:
        return e.code, {}, b""
    except Exception:  # noqa: BLE001
        return 0, {}, b""


def limpo(s) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", str(s or ""))).split())


def ler_acervo(p: Path) -> dict:
    if not p.exists():
        return {}
    with gzip.open(p, "rt", encoding="utf-8") as f:
        return {r["artigo_id"]: r for r in csv.DictReader(f, delimiter=";")}


def gravar_acervo(p: Path, acervo: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    s = io.StringIO()
    w = csv.DictWriter(s, SCOLS, delimiter=";", lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    w.writerows(sorted(acervo.values(), key=lambda r: (r["site_id"], r["publicado_em"], r["artigo_id"]), reverse=True))
    with gzip.GzipFile(p, "wb", mtime=0) as f:
        f.write(s.getvalue().encode("utf-8"))


def robots(base: str, buscar) -> tuple[str, urllib.robotparser.RobotFileParser | None]:
    cod, _, corpo = buscar(base + "/robots.txt")
    if cod != 200 or not corpo:
        return f"sem robots.txt legível (HTTP {cod})", None
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(corpo.decode("utf-8", "replace").splitlines())
    return "lido", rp


def via_rest(site: dict, cfg: dict, desde: str, ate, buscar, com_texto: bool, pausa) -> dict | None:
    """Lê pela API do WordPress. None = a API não está disponível (cai para o RSS)."""
    api = site["base"] + "/wp-json/wp/v2"
    cod, _, corpo = buscar(api + "/types")
    try:
        tipos = json.loads(corpo) if cod == 200 else None
    except ValueError:
        tipos = None
    if not isinstance(tipos, dict):
        return None
    alvo = site.get("tipos") or [k for k, v in tipos.items() if k not in cfg["tipos_ignorados"] and isinstance(v, dict) and v.get("rest_base")]
    pausa()
    cod, _, corpo = buscar(api + "/categories?per_page=100&_fields=id,name")
    try:
        cats = {c["id"]: limpo(c["name"]) for c in json.loads(corpo)} if cod == 200 else {}
    except (ValueError, TypeError, KeyError):
        cats = {}
    campos = "id,date_gmt,modified_gmt,link,type,title,categories,yoast_head_json.author" + (",excerpt,content" if com_texto else "")
    por, linhas, brutos, regs = (50 if com_texto else 100), [], [], []
    for t in alvo:
        rb = (tipos.get(t) or {}).get("rest_base") or t
        pausa()
        cod, cab, _ = buscar(f"{api}/{rb}?per_page=1&_fields=id")
        reg = {"tipo": t, "universo_total": int(cab["x-wp-total"]) if cod == 200 and str(cab.get("x-wp-total", "")).isdigit() else None,
               "universo_no_periodo": None, "lidos": 0, "erro": None if cod == 200 else f"HTTP {cod} ao listar"}
        regs.append(reg)
        if cod != 200:
            continue
        pag, paginas = 1, 1
        while pag <= paginas and pag <= cfg["max_paginas_por_tipo"]:
            q = {"per_page": por, "page": pag, "after": f"{desde}T00:00:00", "orderby": "date", "order": "desc", "_fields": campos}
            if ate:
                q["before"] = f"{ate}T23:59:59"
            pausa()
            cod, cab, corpo = buscar(f"{api}/{rb}?{urllib.parse.urlencode(q)}")
            if cod != 200:
                reg["erro"] = f"HTTP {cod} na página {pag}"
                break
            if pag == 1:
                reg["universo_no_periodo"] = int(cab["x-wp-total"]) if str(cab.get("x-wp-total", "")).isdigit() else None
                paginas = int(cab["x-wp-totalpages"]) if str(cab.get("x-wp-totalpages", "")).isdigit() else 1
            for x in json.loads(corpo):
                linhas.append({"site_id": site["id"], "ator_id": site["ator_id"], "tipo": t, "artigo_id": f"{site['id']}:{t}:{x['id']}", "url": x.get("link") or "",
                               "publicado_em": comum.quando(x.get("date_gmt")), "modificado_em": comum.quando(x.get("modified_gmt")),
                               "titulo": limpo((x.get("title") or {}).get("rendered")), "categorias": "; ".join(cats.get(c, str(c)) for c in x.get("categories") or []),
                               "autor": limpo(comum.g(x, "yoast_head_json.author")), "via": "wp-json"})
                reg["lidos"] += 1
                if com_texto:
                    brutos.append({"artigo_id": linhas[-1]["artigo_id"], "url": linhas[-1]["url"], "publicado_em": linhas[-1]["publicado_em"], "titulo": linhas[-1]["titulo"],
                                   "resumo": limpo((x.get("excerpt") or {}).get("rendered")), "texto": limpo((x.get("content") or {}).get("rendered"))})
            pag += 1
        if reg["erro"]:
            reg["cobertura"] = "parcial ⛔: " + reg["erro"]
        elif reg["universo_no_periodo"] is not None and reg["lidos"] >= reg["universo_no_periodo"]:
            reg["cobertura"] = "completa: lidos todos os que o site informa no período"
        else:
            reg["cobertura"] = "parcial ⛔: lidos menos do que o site informa no período" if reg["universo_no_periodo"] is not None else "⛔ o site não informou o total do período"
    return {"via": "wp-json", "tipos": regs, "linhas": linhas, "brutos": brutos}


def via_rss(site: dict, cfg: dict, desde: str, ate, buscar, com_texto: bool, pausa) -> dict:
    linhas, brutos, chegou, erro, pag = [], [], False, None, 1
    while pag <= cfg["max_paginas_por_tipo"]:
        pausa()
        cod, _, corpo = buscar(f"{site['base']}/feed/?paged={pag}")
        if cod != 200:
            chegou, erro = pag > 1 and cod == 404, None if pag > 1 and cod == 404 else f"HTTP {cod} no RSS (página {pag})"
            break
        try:
            itens = ET.fromstring(corpo).findall("./channel/item")
        except ET.ParseError:
            erro = f"RSS ilegível (página {pag})"
            break
        if not itens:
            chegou = True
            break
        dias = []
        for it in itens:
            try:
                pub = email.utils.parsedate_to_datetime(it.findtext("pubDate") or "").astimezone(comum.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            except (TypeError, ValueError):
                continue
            dias.append(pub[:10])
            if pub[:10] < desde or (ate and pub[:10] > ate):
                continue
            link = (it.findtext("link") or "").strip()
            linhas.append({"site_id": site["id"], "ator_id": site["ator_id"], "tipo": "post", "artigo_id": f"{site['id']}:rss:{(it.findtext('guid') or link).strip()}", "url": link,
                           "publicado_em": pub, "modificado_em": "", "titulo": limpo(it.findtext("title")), "categorias": "; ".join(limpo(c.text) for c in it.findall("category")),
                           "autor": limpo(it.findtext(DC)), "via": "rss"})
            if com_texto:
                brutos.append({"artigo_id": linhas[-1]["artigo_id"], "url": link, "publicado_em": pub, "titulo": linhas[-1]["titulo"],
                               "resumo": limpo(it.findtext("description")), "texto": limpo(it.findtext(CONTEUDO))})
        if dias and all(d < desde for d in dias):
            chegou = True
            break
        pag += 1
    cob = ("parcial ⛔: " + erro) if erro else ("lido até a data inicial; universo ⛔ desconhecido (o RSS não informa total)" if chegou else "parcial ⛔: limite de páginas do RSS")
    return {"via": "rss", "tipos": [{"tipo": "post", "universo_total": None, "universo_no_periodo": None, "lidos": len(linhas), "erro": erro, "cobertura": cob}], "linhas": linhas, "brutos": brutos}


def main(argv=None, buscar=None, root=None) -> int:
    root = Path(root or ".")
    cfg = comum.ler_json(root / "data/config/sites.json")
    desde, ate = comum.periodo(root)
    pasta, agora = root / "data/sites", now_utc()
    interno = os.environ.get("ATLAS_INTERNO_DIR") or os.environ.get("ODI_INTERNO_DIR")
    pausa = (lambda: None) if buscar else (lambda: time.sleep(float(cfg.get("intervalo_s", 1))))
    buscar = buscar or http
    man = {"run_started_utc": agora, "ferramenta": "API pública do WordPress (wp-json) · RSS", "modo": "carga", "user_agent": UA, "periodo": {"desde": desde, "ate": ate},
           "custo_usd": 0.0, "texto_integral": "no repositório privado" if interno else "não pedido (sem repositório privado)", "sites": []}
    acervo, mudou = ler_acervo(pasta / "artigos.csv.gz"), False
    for site in cfg["sites"]:
        reg = {"site_id": site["id"], "base": site["base"]}
        man["sites"].append(reg)
        reg["robots"], rp = robots(site["base"], buscar)
        pode = lambda caminho: rp is None or rp.can_fetch(UA, site["base"] + caminho)  # noqa: E731
        res = None
        if pode("/wp-json/wp/v2/posts"):
            res = via_rest(site, cfg, desde, ate, buscar, bool(interno), pausa)
        else:
            reg["robots"] += " · não permite /wp-json"
        if res is None and pode("/feed/"):
            res = via_rss(site, cfg, desde, ate, buscar, bool(interno), pausa)
        if res is None:
            reg.update(via=None, tipos=[], lidos_no_periodo=0, novos=0, cobertura="⛔ não lido", erro="robots.txt não permite a leitura")
            continue
        novos = 0
        for r in res["linhas"]:
            old = acervo.get(r["artigo_id"]) or {}
            r["primeira_coleta"], r["ultima_coleta"] = old.get("primeira_coleta") or agora, agora
            novos += 0 if old else 1
            acervo[r["artigo_id"]] = r
            mudou = True
        if interno and res["brutos"]:
            d = Path(interno) / "sites"
            d.mkdir(parents=True, exist_ok=True)
            with gzip.open(d / f"{site['id']}_{agora.replace(':', '').replace('-', '')}.jsonl.gz", "wt", encoding="utf-8") as f:
                for x in res["brutos"]:
                    f.write(json.dumps(x, ensure_ascii=False) + "\n")
        erros = [t["erro"] for t in res["tipos"] if t["erro"]]
        lidos_tipos = [t for t in res["tipos"] if not t["erro"]]
        reg.update(via=res["via"], tipos=res["tipos"], lidos_no_periodo=len(res["linhas"]), novos=novos,
                   erro=None if lidos_tipos else (erros[0] if erros else "nenhum tipo de conteúdo listável"),
                   cobertura="⛔ não lido" if not lidos_tipos else ("completa" if all(str(t["cobertura"]).startswith("completa") for t in res["tipos"]) else "parcial ⛔ ou universo desconhecido (ver tipos)"))
        print(f"{site['nome']} ({res['via']}): {len(res['linhas'])} no período, {novos} novos · " +
              " · ".join(f"{t['tipo']}: {t['lidos']} lidos de {t['universo_no_periodo'] if t['universo_no_periodo'] is not None else '⛔'} no período (total do site {t['universo_total'] if t['universo_total'] is not None else '⛔'}){' · ' + t['erro'] if t['erro'] else ''}" for t in res["tipos"]))
    for reg in man["sites"]:
        if reg.get("erro"):
            print(f"{reg['site_id']}: ⛔ {reg['erro']} · robots: {reg['robots']}")
    if mudou:
        gravar_acervo(pasta / "artigos.csv.gz", acervo)
    man.update(artigos_no_acervo=len(acervo), artigos_novos=sum(r.get("novos") or 0 for r in man["sites"]))
    ruins = [r for r in man["sites"] if r.get("erro")]
    status = f"⛔ nenhum site lido: {ruins[0]['erro']}" if len(ruins) == len(man["sites"]) else (f"parcial: {len(ruins)} site(s) não lido(s)" if ruins else "ok")
    man["status"] = status
    comum.gravar_manifesto(pasta, man)
    print(f"sites: {status} · acervo {len(acervo)}")
    return 1 if status.startswith("⛔") else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
