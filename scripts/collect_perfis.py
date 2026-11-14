#!/usr/bin/env python3
"""Seguidores e total de publicações que a plataforma informa (o universo), por perfil.

Porta do collect_meta_apify.py do ODI Atlas (atores oficiais apify/instagram-profile-scraper e apify/facebook-pages-scraper),
sem consulta de saldo. No X esses números vêm do próprio post (scripts/collect_x_posts.py), sem custo extra.

--diario  perfis confirmados de Instagram e Facebook → data/perfis/latest.csv e perfis_AAAA-MM-DD.csv (uma foto por dia).
--sonda   apoio à conferência dos perfis de data/config/atores.json: lê nome exibido, selo, seguidores e total de posts
          dos confirmados e dos candidatos (inclusive X, com 1 post por perfil). NÃO confirma nada: quem confirma é uma
          pessoa, abrindo o perfil. Como um candidato pode ser a conta de outra pessoa com nome parecido, a ficha dos
          candidatos vai só para o repositório privado (ATLAS_INTERNO_DIR/perfis/); sem ele, os candidatos não são sondados.

Teto em data/config/coleta.json → perfis (0 = sem autorização). Manifestos em data/perfis/manifesto-*.json.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comum  # noqa: E402
from apify import custo_run, erro_curto, run_actor  # noqa: E402
from collect_x_posts import autor as autor_x  # noqa: E402
from comum import g, inteiro  # noqa: E402
from net import now_utc  # noqa: E402


def chave_fb(url: str) -> str:
    return url.lower().split("?")[0].rstrip("/").replace("://m.", "://www.").replace("://facebook", "://www.facebook")


def ficha(rede: str, it: dict) -> tuple[str, dict]:
    """(chave do perfil em minúsculas, o que a plataforma informa). Número ausente fica None."""
    num = lambda *ks: (lambda v: None if v == "" else v)(inteiro(g(it, *ks)))  # noqa: E731
    if rede == "instagram":
        return str(it.get("username") or "").lower(), {
            "nome_exibido": it.get("fullName") or "", "verificado": it.get("verified"), "privado": it.get("private"),
            "seguidores": num("followersCount", "followers"), "posts_total": num("postsCount"), "bio": str(it.get("biography") or "")[:200]}
    if rede == "facebook":
        return chave_fb(str(g(it, "pageUrl", "facebookUrl", "url") or "")), {
            "nome_exibido": g(it, "title", "pageName", "name") or "", "verificado": it.get("verified"), "privado": None,
            "seguidores": num("followers", "followersCount", "likes"), "posts_total": None, "bio": str(g(it, "intro", "info.0") or "")[:200]}
    return autor_x(it).lower(), {
        "nome_exibido": g(it, "author.name", "user.name") or "", "verificado": g(it, "author.isBlueVerified", "author.isVerified", "user.verified"), "privado": None,
        "seguidores": num("author.followers", "author.followersCount", "user.followers_count"),
        "posts_total": num("author.statusesCount", "author.statuses_count", "user.statuses_count"), "bio": str(g(it, "author.description", "user.description") or "")[:200]}


def pedido(rede: str, alvos: list[dict]) -> dict:
    if rede == "instagram":
        return {"usernames": [p["perfil"] for p in alvos]}
    if rede == "facebook":
        return {"startUrls": [{"url": p["url"]} for p in alvos]}
    return {"searchTerms": [f"from:{p['perfil']}" for p in alvos], "maxItems": 2 * len(alvos), "queryType": "Latest"}


def main(argv=None, executar=None, root=None, hoje=None) -> int:
    argv, root = list(argv or []), Path(root or ".")
    modo = "sonda" if "--sonda" in argv else "diario" if "--diario" in argv else None
    if not modo:
        print("uso: collect_perfis.py --sonda | --diario")
        return 2
    hoje = hoje or comum.hoje_brt()
    geral = comum.ler_json(root / "data/config/coleta.json")
    P = geral["perfis"]
    _, ate = comum.periodo(root)
    if modo == "diario" and ate and hoje.isoformat() > ate:
        print(f"perfis: período encerrado em {ate}; o diário não roda mais (sem custo)")
        return 0
    pasta, agora = root / "data/perfis", now_utc()
    mans = comum.manifestos(pasta)
    if modo == "sonda":
        ja, teto_cfg = comum.gasto(mans, "sonda"), float(P["sonda"]["teto_usd"])
        teto = round(teto_cfg - ja, 5)
    else:
        ja, teto_cfg = comum.gasto(mans, "diario", agora[:7]), float(P["diario"]["teto_mes_usd"])
        teto = round(min(float(P["diario"]["teto_dia_usd"]), teto_cfg - ja), 5)
    interno = os.environ.get("ATLAS_INTERNO_DIR") or os.environ.get("ODI_INTERNO_DIR")
    man = {"run_started_utc": agora, "modo": modo, "conta": geral["segredo"], "teto_autorizado_usd": teto_cfg, "gasto_antes_usd": ja,
           "teto_execucao_usd": max(teto, 0.0), "execucoes": [], "perfis": []}

    def fim(status: str, code: int) -> int:
        man["status"] = status
        comum.gravar_manifesto(pasta, man)
        print(f"perfis ({modo}): {status}")
        return code

    if teto_cfg <= 0 or (modo == "diario" and float(P["diario"]["teto_dia_usd"]) <= 0):
        return fim(f"⛔ sem autorização de gasto registrada (data/config/coleta.json → perfis.{modo})", 1)
    if teto < 0.01:
        return fim(f"⛔ teto autorizado esgotado (gasto US$ {ja} de US$ {teto_cfg})", 1)
    token = "x" if executar else os.environ.get(geral["segredo"], "").strip()
    if not token:
        return fim(f"⛔ {geral['segredo']} ausente (cadastre o segredo no GitHub)", 1)
    executar = executar or (lambda ator, pl, cap: run_actor(token, ator, pl, cap))

    redes = comum.REDES if modo == "sonda" else ("instagram", "facebook")
    por_rede = {}
    for rede in redes:
        conf, fora = comum.perfis_da_rede(root, rede)
        cand = [p for p in fora if p["perfil"]] if modo == "sonda" and interno else []
        if modo == "sonda" and not interno:
            man["candidatos_nao_sondados"] = man.get("candidatos_nao_sondados", 0) + sum(1 for p in fora if p["perfil"])
        if conf + cand:
            por_rede[rede] = conf + cand
    if not por_rede:
        return fim("⛔ nenhum perfil para ler", 1)

    sobra, publicas, privadas = teto, [], []
    for i, (rede, alvos) in enumerate(por_rede.items()):
        ator = geral["redes"]["x"]["ator"] if rede == "x" else P["atores"][rede]
        cap = round(sobra / (len(por_rede) - i), 4)
        ex = {"rede": rede, "ator": ator, "perfis_pedidos": len(alvos), "teto_usd": cap}
        man["execucoes"].append(ex)
        achados = {}
        try:
            run, itens = executar(ator, pedido(rede, alvos), cap)
            custo = min(cap, custo_run(run or {}))
            sobra = round(sobra - custo, 5)
            ex.update(run=(run or {}).get("id"), itens=len(itens or []), custo_usd=custo)
            for it in itens or []:
                if isinstance(it, dict) and not it.get("error") and not it.get("noResults"):
                    k, f = ficha(rede, it)
                    if k:
                        achados.setdefault(k, f)
        except Exception as e:  # noqa: BLE001
            ex["erro"] = erro_curto(e)
        for p in alvos:
            f = achados.get(chave_fb(p["url"]) if rede == "facebook" else p["perfil"].lower())
            base = {"ator_id": p["ator_id"], "ator_nome": p["ator_nome"], "rede": rede, "perfil": p["perfil"], "url": p["url"],
                    "confirmado": p["confirmado"], "encontrado": bool(f)}
            (publicas if p["confirmado"] else privadas).append({**base, **(f or {})})
            man["perfis"].append({"ator_id": p["ator_id"], "rede": rede, "confirmado": p["confirmado"], "encontrado": bool(f),
                                  **({"perfil": p["perfil"], "seguidores": (f or {}).get("seguidores"), "posts_total": (f or {}).get("posts_total")} if p["confirmado"] else {})})

    pasta.mkdir(parents=True, exist_ok=True)
    if modo == "sonda":
        (pasta / "sonda.json").write_text(json.dumps({"lido_em_utc": agora, "nota": "Só perfis confirmados. A ficha dos candidatos fica no repositório privado.", "perfis": publicas}, ensure_ascii=False, indent=1), encoding="utf-8")
        if interno and privadas:
            d = Path(interno) / "perfis"
            d.mkdir(parents=True, exist_ok=True)
            (d / f"sonda_candidatos_{agora.replace(':', '').replace('-', '')}.json").write_text(json.dumps(privadas, ensure_ascii=False, indent=1), encoding="utf-8")
        man["candidatos_sondados"] = len(privadas)
    else:
        linhas = [{"ator_id": p["ator_id"], "ator_nome": p["ator_nome"], "rede": p["rede"], "perfil": p["perfil"], "url": p["url"],
                   "nome_exibido": p.get("nome_exibido") or "", "seguidores": "" if p.get("seguidores") is None else p["seguidores"],
                   "posts_total": "" if p.get("posts_total") is None else p["posts_total"],
                   "verificado": "" if p.get("verificado") is None else ("sim" if p["verificado"] else "não"), "captured_at": agora[:10],
                   "fonte": "Apify · " + (geral["perfis"]["atores"][p["rede"]]).replace("~", "/")} for p in publicas if p["encontrado"]]
        if linhas:
            for nome in (f"perfis_{agora[:10]}.csv", "latest.csv"):
                with open(pasta / nome, "w", encoding="utf-8", newline="") as fh:
                    w = csv.DictWriter(fh, comum.PCOLS, delimiter=";", lineterminator="\n")
                    w.writeheader()
                    w.writerows(linhas)
    man["custo_usd"] = round(teto - sobra, 5)
    erros = [e for e in man["execucoes"] if e.get("erro")]
    nao = [p for p in man["perfis"] if p["confirmado"] and not p["encontrado"]]
    if len(erros) == len(man["execucoes"]):
        return fim(f"⛔ nenhuma rede lida: {erros[0]['erro']}", 1)
    if erros or nao:
        return fim(f"parcial: {len(erros)} rede(s) com erro, {len(nao)} perfil(is) confirmado(s) sem resposta", 0)
    return fim("ok", 0)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
