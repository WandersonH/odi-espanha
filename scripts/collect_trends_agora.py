#!/usr/bin/env python3
"""Google Trends "Em alta agora" (Espanha) e Google Notícias (primeiros resultados por termo), pelos RSS públicos do Google.

Sem custo, sem chave e sem login. Versão enxuta do coletor do ODI Atlas (collect_trends_agora.py): lê os mesmos dois endereços
públicos, sem a parte específica dos debates. O Google não informa quantas buscas ou notícias existem ao todo: aqui fica o que
o RSS entrega na hora da leitura, na ordem do Google, e isso é dito na página.

Saídas: data/trends/agora.json (lista da leitura) e data/trends/agora_historico.csv (uma linha por busca e leitura);
        data/trends/noticias.json (5 primeiros por termo) e data/trends/noticias_historico.csv (primeira leitura de cada dia).
"""
from __future__ import annotations

import csv
import email.utils
import json
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import texto as tx  # noqa: E402
from net import now_utc, open_url, read_body  # noqa: E402

RSS_ALTA = "https://trends.google.com/trending/rss?geo={geo}"
RSS_NOTICIAS = "https://news.google.com/rss/search?"
ATORES = ["vox", "abascal", "disenso", "foro madrid", "martin frias", "cader"]


def _t(el, nome):
    """Texto do primeiro filho cujo nome (sem o prefixo do namespace) é `nome`."""
    for f in el:
        if f.tag.split("}")[-1] == nome:
            return (f.text or "").strip()
    return ""


def _data(s: str) -> str:
    try:
        return email.utils.parsedate_to_datetime(s).astimezone(email.utils.datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:  # noqa: BLE001
        return ""


def cita_ator(*textos: str) -> bool:
    n = tx.norm(" ".join(textos))
    return any(f" {a} " in n for a in ATORES)


def parse_alta(xml: str) -> list[dict]:
    out = []
    for i, it in enumerate(ET.fromstring(xml).iter("item"), 1):
        nts = [{"titulo": _t(n, "news_item_title"), "fonte": _t(n, "news_item_source"), "url": _t(n, "news_item_url")} for n in it if n.tag.split("}")[-1] == "news_item"]
        termo = _t(it, "title")
        out.append({"pos": i, "termo": termo, "trafego_aproximado": _t(it, "approx_traffic"), "publicado_em": _data(_t(it, "pubDate")), "noticias": nts[:3],
                    "cita_ator": cita_ator(termo, *[n["titulo"] for n in nts])})
    return out


def parse_noticias(xml: str, n: int = 5) -> list[dict]:
    out = []
    for i, it in enumerate(ET.fromstring(xml).iter("item"), 1):
        if i > n:
            break
        fonte = _t(it, "source")
        titulo = _t(it, "title")
        out.append({"pos": i, "titulo": titulo[: -len(fonte) - 3] if fonte and titulo.endswith(" - " + fonte) else titulo, "fonte": fonte, "url": _t(it, "link"), "publicado_em": _data(_t(it, "pubDate"))})
    return out


def baixar(url: str) -> str:
    with open_url(url, timeout=60, headers={"User-Agent": "Mozilla/5.0 (compatible; ODI-Espanha/1.0; pesquisa acadêmica)", "Accept-Language": "es-ES,es;q=0.9"}) as r:
        return read_body(r).decode("utf-8", "replace")


def _anexar(arq: Path, cols: list[str], linhas: list[dict], chave) -> None:
    antigas = list(csv.DictReader(open(arq, encoding="utf-8"), delimiter=";")) if arq.exists() else []
    vistas = {chave(r) for r in antigas}
    with open(arq, "w", encoding="utf-8", newline="") as h:
        w = csv.DictWriter(h, cols, delimiter=";", lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(antigas + [r for r in linhas if chave(r) not in vistas])


def main(argv=None, buscar=None, root=None) -> int:
    root = Path(root or ".")
    cfg = json.loads((root / "data/config/trends.json").read_text(encoding="utf-8"))
    geo, agora, buscar = cfg.get("geo", "ES"), now_utc(), buscar or baixar
    pasta = root / "data/trends"
    pasta.mkdir(parents=True, exist_ok=True)
    ok = 0
    try:
        itens = parse_alta(buscar(RSS_ALTA.format(geo=geo)))
        (pasta / "agora.json").write_text(json.dumps({"coletado_em_utc": agora, "geo": geo, "fonte": "Google Trends · Em alta agora (RSS público)",
            "nota": "Lista que o Google publica no momento da leitura, na ordem dele. O volume é a faixa aproximada que o Google informa, não uma contagem. Uma leitura por execução; a lista muda ao longo do dia.",
            "itens": itens}, ensure_ascii=False, indent=1), encoding="utf-8")
        _anexar(pasta / "agora_historico.csv", ["coletado_em_utc", "pos", "termo", "trafego_aproximado", "cita_ator"], [{**i, "coletado_em_utc": agora} for i in itens], lambda r: (r["coletado_em_utc"], r["termo"]))
        print(f"em alta agora ({geo}): {len(itens)} buscas · citam os atores: {sum(1 for i in itens if i['cita_ator'])}")
        ok += bool(itens)
    except Exception as e:  # noqa: BLE001
        print(f"em alta agora: ⛔ não lido ({type(e).__name__})")
    termos, res, erros = cfg.get("noticias_termos") or [], {}, []
    for t in termos:
        try:
            res[t] = parse_noticias(buscar(RSS_NOTICIAS + urllib.parse.urlencode({"q": t, "hl": "es", "gl": geo, "ceid": f"{geo}:es"})))
        except Exception as e:  # noqa: BLE001
            erros.append(f"{t}: {type(e).__name__}")
    if res:
        (pasta / "noticias.json").write_text(json.dumps({"coletado_em_utc": agora, "geo": geo, "fonte": "Google Notícias · busca por termo (RSS público)",
            "nota": "Os 5 primeiros resultados de cada termo na ordem do Google Notícias na hora da leitura. O Google não informa quantas notícias existem ao todo sobre o termo.",
            "termos": res, "erros": erros}, ensure_ascii=False, indent=1), encoding="utf-8")
        _anexar(pasta / "noticias_historico.csv", ["dia", "termo", "pos", "titulo", "fonte", "url", "publicado_em"],
                [{**n, "dia": agora[:10], "termo": t} for t, ns in res.items() for n in ns], lambda r: (r["dia"], r["termo"], str(r["pos"])))
        ok += 1
    print(f"google notícias: {sum(len(v) for v in res.values())} resultados em {len(res)} de {len(termos)} termos" + (f" · erros: {'; '.join(erros)}" if erros else ""))
    return 0 if ok == 2 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
