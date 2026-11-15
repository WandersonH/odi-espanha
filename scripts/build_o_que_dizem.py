#!/usr/bin/env python3
"""Caderno "O que dizem": publicações de cada ator por tema, por rede, com as regras do caderno "O que as campanhas
dizem" do ODI Atlas (scripts/build_tiktok.py e build_conteudo.py de lá).

Entrada: data/<rede>/posts.csv.gz, data/<rede>/manifesto_latest.json, data/config/temas.json (dicionário em espanhol).
Saída:   data/<rede>/conteudo.json, no mesmo desenho do Atlas, com um bloco por ator em vez de um por candidato.

Como no Atlas: links removidos; trechos repetidos em 10+ publicações do mesmo perfil descartados; nuvem e hashtags
contadas por nº de publicações; taxa de interação = (curtidas + comentários + compartilhamentos) ÷ visualizações
(interação por visualização; não mede apoio); marcas "cita adversário" e "pede voto". O dicionário diz quanto do
acervo ele cobre (publicações com pelo menos um tema): parte "sem tema" alta é sinal de dicionário incompleto.
"""
from __future__ import annotations

import datetime as dt
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comum  # noqa: E402
import texto as tx  # noqa: E402


def num(v):
    return int(v) if str(v or "").strip().lstrip("-").isdigit() else None


def taxa(r: dict):
    v = num(r["visualizacoes"])
    return None if not v else sum(num(r[k]) or 0 for k in ("curtidas", "comentarios", "compartilhamentos")) / v


def main(argv=None, root=None) -> int:
    root = Path(root or ".")
    cfg = comum.ler_json(root / "data/config/temas.json")
    temas, adv, voto = tx.compilar(cfg)
    brasil = tx.compilar_brasil(cfg)
    desde, ate = comum.periodo(root)
    atores = comum.ler_json(root / "data/config/atores.json")["atores"]
    for rede in comum.REDES:
        rows = sorted(comum.ler_acervo(root / "data" / rede / "posts.csv.gz").values(), key=lambda r: r["publicado_em"], reverse=True)
        if not rows:
            print(f"{rede}: ⛔ sem acervo, conteudo.json não gerado")
            continue
        man_p = root / "data" / rede / "manifesto_latest.json"
        man = json.loads(man_p.read_text(encoding="utf-8")) if man_p.exists() else {}
        padrao = tx.texto_padrao(rows)
        out = {"schema_version": 1, "gerado_em_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "rede": rede,
               "coletado_em_utc": man.get("run_started_utc"), "status_coleta": man.get("status"), "ferramenta": man.get("ferramenta"),
               "fonte": f"{comum.ROTULO[rede]} público: perfis confirmados em data/config/atores.json",
               "metodo": cfg["nota"] + f" Links removidos e trechos repetidos em {tx.LIMIAR_REPETICAO}+ publicações do mesmo perfil descartados. Taxa de interação = (curtidas + comentários + compartilhamentos) ÷ visualizações; não mede apoio.",
               "dicionario": {"versao": cfg["versao"], "estado": cfg["estado"]}, "temas": list(cfg["temas"]) + ["sem_tema"],
               "desde": desde, "ate": ate, "fases": cfg["fases"], "fases_nota": cfg.get("fases_nota"), "atores": {}}
        com_tema = 0
        for a in atores:
            meus = [r for r in rows if r["ator_id"] == a["id"]]
            if not meus:
                continue
            nome = tx.norm(a["nome"]).split()
            excluir = set(nome) | {"".join(nome)} | {tx.tag_key(r["perfil"]) for r in meus}
            pubs, textos, tags = [], [], []
            for r in meus:
                util = tx.texto_util(r, padrao)
                textos.append(util)
                tg = {tx.tag_key(t) for t in tx.HASHTAG.findall(r["texto"])} - excluir
                tags.append(tg)
                c = tx.classificar(util, temas, adv, voto, brasil)
                t_ = taxa(r)
                pubs.append({"post_id": r["post_id"], "perfil": r["perfil"], "url": r["url"], "texto": r["texto"][:400], "tipo": r["tipo"], "publicado_em": r["publicado_em"],
                             **{k: num(r[k]) for k in ("visualizacoes", "curtidas", "comentarios", "compartilhamentos")},
                             "taxa_interacao": round(t_, 4) if t_ is not None else None, "hashtags": sorted(tg), **c})
            com_tema += sum(1 for p in pubs if p["temas"] != ["sem_tema"])
            por_tema, views_tema = Counter(t for p in pubs for t in p["temas"]), Counter()
            for p in pubs:
                for t in p["temas"]:
                    views_tema[t] += p["visualizacoes"] or 0
            taxas = [p["taxa_interacao"] for p in pubs if p["taxa_interacao"] is not None]
            fase = {}
            for f in cfg["fases"]:
                ps = [p for p in pubs if f["de"] <= p["publicado_em"][:10] <= f["ate"]]
                tf = [p["taxa_interacao"] for p in ps if p["taxa_interacao"] is not None]
                fase[f["id"]] = {"rotulo": f["rotulo"], "de": f["de"], "ate": f["ate"], "publicacoes": len(ps), "visualizacoes": sum(p["visualizacoes"] or 0 for p in ps),
                                 "taxa_interacao_mediana": round(statistics.median(tf), 4) if tf else None,
                                 "nuvem": tx.nuvem([t for t, p in zip(textos, pubs) if f["de"] <= p["publicado_em"][:10] <= f["ate"]], excluir),
                                 "hashtags": [[t, n] for t, n in Counter(t for s, p in zip(tags, pubs) if f["de"] <= p["publicado_em"][:10] <= f["ate"] for t in s).most_common(40) if n >= 2]}
            out["atores"][a["id"]] = {
                "nome": a["nome"], "total_publicacoes": len(pubs), "perfis": dict(Counter(p["perfil"] for p in pubs).most_common()),
                "totais": {k: sum(p[k] or 0 for p in pubs) for k in ("visualizacoes", "curtidas", "comentarios", "compartilhamentos")},
                "com_o_numero": {k: sum(1 for p in pubs if p[k] is not None) for k in ("visualizacoes", "curtidas", "comentarios", "compartilhamentos")},
                "taxa_interacao_mediana": round(statistics.median(taxas), 4) if taxas else None,
                "por_tema": dict(por_tema.most_common()), "visualizacoes_por_tema": dict(views_tema.most_common()),
                "cita_adversario": sum(p["cita_adversario"] for p in pubs), "pede_voto": sum(p["pede_voto"] for p in pubs),
                "cita_brasil": sum(p["cita_brasil"] for p in pubs),
                "nuvem": tx.nuvem(textos, excluir), "hashtags": [[t, n] for t, n in Counter(t for s in tags for t in s).most_common(40) if n >= 2],
                "por_mes": dict(sorted(Counter(p["publicado_em"][:7] for p in pubs).items())), "por_fase": fase, "publicacoes": pubs}
        out["cita_brasil_nota"], out["cita_brasil_termos"] = cfg.get("cita_brasil_nota"), cfg.get("cita_brasil")
        out["cobertura_do_dicionario"] = {"publicacoes": len(rows), "com_tema": com_tema, "sem_tema": len(rows) - com_tema, "pct_com_tema": round(100 * com_tema / len(rows), 1)}
        (root / "data" / rede / "conteudo.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        tot = Counter(t for a in out["atores"].values() for t, n in a["por_tema"].items() for _ in range(n))
        print(f"{rede}: {len(rows)} publicações · {out['cobertura_do_dicionario']['pct_com_tema']}% com tema · " + " · ".join(f"{t} {n}" for t, n in tot.most_common(6)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
