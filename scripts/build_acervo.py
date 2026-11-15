#!/usr/bin/env python3
"""Agrega o acervo de posts para a página: data/site/resumo.json, indice.json e posts-AAAA-MM.json.

Lê só arquivos publicados (data/<rede>/posts.csv.gz, manifestos, data/perfis/*.csv e a configuração). Nada é estimado:
- universo = o que a plataforma informa (total de publicações do perfil, com data e fonte); quando ela não informa, fica
  None e a página mostra ⛔ desconhecido;
- o total de publicações dentro do período nenhuma das três redes informa: a cobertura do período vem da própria leitura
  (parou pela data = completa; parou no limite = parcial ⛔), registrada no manifesto da carga;
- sem coleta, os números ficam None (a página mostra ⛔ sem coleta), nunca zero.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comum  # noqa: E402
from net import now_utc  # noqa: E402

RE_TAG = re.compile(r"(?<!\w)#(\w{2,60})")
RE_ARROBA = re.compile(r"(?<![\w@./])@([A-Za-z0-9_](?:[A-Za-z0-9_.]{0,28}[A-Za-z0-9_])?)")
NUM = ("visualizacoes", "curtidas", "comentarios", "compartilhamentos")
CURTO = {"visualizacoes": "v", "curtidas": "c", "comentarios": "m", "compartilhamentos": "s"}


def num(v):
    return int(v) if str(v).lstrip("-").isdigit() else None


def universos(root: Path) -> dict:
    """(rede, perfil em minúsculas) → o que a plataforma informou, da foto mais recente."""
    out = {}
    for nome in ("latest.csv", "x_latest.csv", "youtube_latest.csv"):
        p = root / "data/perfis" / nome
        if not p.exists():
            continue
        with open(p, encoding="utf-8") as f:
            for r in csv.DictReader(f, delimiter=";"):
                out[(r["rede"], r["perfil"].lower())] = {"posts_total_plataforma": num(r.get("posts_total")), "seguidores": num(r.get("seguidores")),
                                                          "nome_exibido": r.get("nome_exibido") or "", "lido_em": r.get("captured_at"), "fonte": r.get("fonte") or ""}
    sonda = root / "data/perfis/sonda.json"   # leitura avulsa do universo: vale onde ainda não há foto diária
    if sonda.exists():
        s = json.loads(sonda.read_text(encoding="utf-8"))
        for r in s.get("perfis") or []:
            if r.get("encontrado") and (r["rede"], r["perfil"].lower()) not in out:
                out[(r["rede"], r["perfil"].lower())] = {"posts_total_plataforma": r.get("posts_total"), "seguidores": r.get("seguidores"), "nome_exibido": r.get("nome_exibido") or "",
                                                          "lido_em": (s.get("lido_em_utc") or "")[:10], "fonte": "sonda de perfis (Apify, atores oficiais)"}
    return out


def leituras(root: Path, rede: str) -> tuple[dict, dict, dict | None]:
    """Por perfil: registro da última carga (mede cobertura) e da última leitura de qualquer modo; e o último manifesto."""
    carga, ultima, ultimo_man = {}, {}, None
    for m in comum.manifestos(root / "data" / rede):
        ultimo_man = m
        for r in m.get("perfis") or []:
            reg = {"modo": m.get("modo"), "quando": m.get("run_started_utc"), **{k: r.get(k) for k in
                   ("pedido", "itens", "lidos_no_periodo", "mais_antigo", "mais_recente", "cobertura", "erro", "complemento_erro")}}
            k = (r.get("perfil") or "").lower()
            ultima[k] = reg
            if m.get("modo") == "carga" and not r.get("erro"):
                carga[k] = reg
    return carga, ultima, ultimo_man


def resumo_sites(root: Path) -> dict:
    """Notícias e artigos dos sites oficiais: o que cada site informa (universo), o que foi lido e a lista para a página."""
    import collect_sites
    cfg = comum.ler_json(root / "data/config/sites.json")
    acervo = sorted(collect_sites.ler_acervo(root / "data/sites/artigos.csv.gz").values(), key=lambda r: (r["publicado_em"], r["artigo_id"]), reverse=True)
    ultima = {}
    for m in comum.manifestos(root / "data/sites"):
        for s in m.get("sites") or []:
            ultima[s["site_id"]] = {"quando": m.get("run_started_utc"), **{k: s.get(k) for k in ("via", "robots", "tipos", "lidos_no_periodo", "cobertura", "erro")}}
    sites = []
    for s in cfg["sites"]:
        meus = [r for r in acervo if r["site_id"] == s["id"]]
        sites.append({"id": s["id"], "nome": s["nome"], "ator_id": s["ator_id"], "base": s["base"], "artigos_no_acervo": len(meus) if meus or s["id"] in ultima else None,
                      "primeiro": meus[-1]["publicado_em"] if meus else None, "ultimo": meus[0]["publicado_em"] if meus else None, "leitura": ultima.get(s["id"])})
    por_mes = Counter((r["publicado_em"][:7], r["site_id"]) for r in acervo)
    return {"gerado_em_utc": now_utc(), "nota": cfg.get("nota", ""), "sites": sites,
            "por_mes": [{"mes": m, "site_id": s, "artigos": n} for (m, s), n in sorted(por_mes.items())],
            "artigos": [{"s": r["site_id"], "k": r["tipo"], "d": r["publicado_em"], "t": r["titulo"], "u": r["url"], "c": r["categorias"], "a": r["autor"]} for r in acervo]}


def main(argv=None, root=None) -> int:
    root = Path(root or ".")
    proj = comum.ler_json(root / "data/config/projeto.json")
    atores = comum.ler_json(root / "data/config/atores.json")["atores"]
    uni = universos(root)
    posts, perfis, estado_rede = [], [], {}
    for rede in comum.REDES:
        acervo = comum.ler_acervo(root / "data" / rede / "posts.csv.gz")
        posts += list(acervo.values())
        carga, ultima, man = leituras(root, rede)
        estado_rede[rede] = {"coletada": bool(acervo), "ultima_execucao": (man or {}).get("run_started_utc"), "status_ultima": (man or {}).get("status"),
                             "modo_ultima": (man or {}).get("modo")}
        conf, fora = comum.perfis_da_rede(root, rede)
        for p in conf + fora:
            meus = [r for r in acervo.values() if r["perfil"].lower() == p["perfil"].lower()] if p["perfil"] else []
            datas = sorted(r["publicado_em"] for r in meus)
            k = p["perfil"].lower()
            perfis.append({**{c: p[c] for c in ("ator_id", "ator_nome", "rede", "perfil", "url", "confirmado", "fonte", "nota")},
                           "situacao": "confirmado" if p["confirmado"] else ("candidato a conferir" if p["perfil"] else "não localizado"),
                           "posts_no_acervo": len(meus) if meus or k in ultima else None,
                           "primeiro": datas[0] if datas else None, "ultimo": datas[-1] if datas else None,
                           "universo": uni.get((rede, k)), "universo_no_periodo": None,
                           "cobertura_do_periodo": (carga.get(k) or {}).get("cobertura"),
                           "carga": carga.get(k), "ultima_leitura": ultima.get(k)})
    posts.sort(key=lambda r: (r["publicado_em"], r["post_id"]), reverse=True)

    por_mes, tags, arrobas = Counter(), defaultdict(Counter), defaultdict(Counter)
    soma = defaultdict(lambda: {c: [0, 0] for c in NUM})  # (ator, rede) → campo → [soma, posts com o número]
    for r in posts:
        por_mes[(r["publicado_em"][:7], r["ator_id"], r["rede"])] += 1
        for t in {t.lower() for t in RE_TAG.findall(r["texto"])}:
            tags[r["ator_id"]][t] += 1
        if r["rede"] != "facebook":  # no Facebook a marcação não aparece como @conta no texto
            for a in {a.lower() for a in RE_ARROBA.findall(r["texto"])} - {r["perfil"].lower()}:
                arrobas[(r["ator_id"], r["rede"])][a] += 1
        for c in NUM:
            v = num(r.get(c))
            if v is not None:
                soma[(r["ator_id"], r["rede"])][c][0] += v
                soma[(r["ator_id"], r["rede"])][c][1] += 1

    site = root / "data/site"
    site.mkdir(parents=True, exist_ok=True)
    for velho in site.glob("posts-*.json"):
        velho.unlink()  # derivados: sempre regerados a partir do acervo
    meses = defaultdict(list)
    for r in posts:
        meses[r["publicado_em"][:7]].append({"i": r["post_id"], "a": r["ator_id"], "r": r["rede"], "p": r["perfil"], "d": r["publicado_em"], "t": r["texto"],
                                             "k": r["tipo"], "u": r["url"], **{CURTO[c]: num(r.get(c)) for c in NUM}})
    for mes, linhas in meses.items():
        (site / f"posts-{mes}.json").write_text(json.dumps(linhas, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (site / "indice.json").write_text(json.dumps({"meses": [{"mes": m, "posts": len(meses[m]), "arquivo": f"posts-{m}.json"} for m in sorted(meses, reverse=True)]},
                                                 ensure_ascii=False, indent=1), encoding="utf-8")
    conf_n = sum(1 for p in perfis if p["confirmado"])
    resumo = {
        "gerado_em_utc": now_utc(),
        "projeto": {k: proj.get(k) for k in ("nome", "descricao", "periodo", "creditos", "fuso_das_datas", "repositorios", "contexto")},
        "totais": {"posts": len(posts) if posts else None, "atores": len(atores), "perfis_previstos": len(perfis), "perfis_confirmados": conf_n,
                   "perfis_candidatos": sum(1 for p in perfis if p["situacao"] == "candidato a conferir"),
                   "perfis_nao_localizados": sum(1 for p in perfis if p["situacao"] == "não localizado"),
                   "perfis_com_posts": sum(1 for p in perfis if p["posts_no_acervo"]),
                   "primeiro_post": posts[-1]["publicado_em"] if posts else None, "ultimo_post": posts[0]["publicado_em"] if posts else None},
        "redes": estado_rede,
        "atores": [{k: a.get(k) for k in ("id", "nome", "tipo", "descricao", "descricao_fonte")} for a in atores],
        "perfis": perfis,
        "por_mes": [{"mes": m, "ator_id": a, "rede": r, "posts": n} for (m, a, r), n in sorted(por_mes.items())],
        "numeros": [{"ator_id": a, "rede": r, **{c: {"soma": v[c][0], "posts_com_o_numero": v[c][1]} for c in NUM}} for (a, r), v in sorted(soma.items())],
        "hashtags": [{"ator_id": a, "tag": t, "posts": n} for a, c in sorted(tags.items()) for t, n in c.most_common(15)],
        "mencoes": [{"ator_id": a, "rede": r, "conta": t, "posts": n} for (a, r), c in sorted(arrobas.items()) for t, n in c.most_common(15)],
    }
    (site / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=1), encoding="utf-8")
    rs = resumo_sites(root)
    (site / "sites.json").write_text(json.dumps(rs, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"sites: {len(rs['artigos'])} notícias e artigos de {sum(1 for s in rs['sites'] if s['artigos_no_acervo'])} site(s)")
    print(f"acervo: {len(posts)} posts · {conf_n} de {len(perfis)} perfis confirmados · {len(meses)} mês(es)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
