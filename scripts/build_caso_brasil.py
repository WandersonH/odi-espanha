#!/usr/bin/env python3
"""Caso "Brasil": cruzamento de TODAS as fontes do Atlas com citações ao Brasil, a Lula e à família Bolsonaro (Flávio à parte).

Fontes e universo de cada uma (o universo é o que foi lido; a regra conta quantos citam):
  - publicações dos perfis: data/<rede>/posts.csv.gz (Instagram, X, Facebook, YouTube) e data/telegram/posts.csv.gz;
  - artigos dos sites oficiais: título (público, data/sites/artigos.csv.gz) e, com o repositório privado, texto integral;
  - comentários do YouTube: só com o repositório privado; ao público vão apenas contagens (comentário é dado de terceiros).
Regra: a mesma lista `cita_brasil` de data/config/temas.json, por palavra e sem IA, separada em quatro grupos:
Brasil, Lula, família Bolsonaro e, dentro dela, Flávio Bolsonaro. A etiqueta diz que o texto cita, não se a citação é
favorável ou crítica.

Saídas públicas: data/casos/brasil.json (resumo, matriz ator × fonte, grupos, meses, itens de autoria dos perfis) e
data/casos/brasil_itens.csv (planilha de conferência). Sem o privado, as fontes que dependem dele ficam ⛔ e o arquivo
anterior não é sobrescrito nessas partes (são reaproveitadas do arquivo anterior, com a data da leitura delas).
"""
from __future__ import annotations

import csv
import datetime as dt
import glob
import gzip
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comum  # noqa: E402
import texto as tx  # noqa: E402

GRUPOS = {
    "brasil": ("Brasil", ["brasil*", "brazil*"]),
    "lula": ("Lula", ["lula", "lulaoficial", "luladasilva", "lulismo", "lulista", "lulistas", "lulalibre", "lulalivre"]),
    "bolsonaro": ("Família Bolsonaro", ["bolsonaro*", "jairbolsonaro", "flaviobolsonaro", "eduardobolsonaro", "carlosbolsonaro", "michellebolsonaro"]),
    "flavio": ("Flávio Bolsonaro", ["flavio bolsonaro", "flaviobolsonaro", "flavio bolsonaro*"]),
}
REDES = {"instagram": "Instagram", "x": "X", "facebook": "Facebook", "youtube": "YouTube", "telegram": "Telegram"}


def compilar() -> dict:
    return {g: [tx.term_regex(t) for t in ts] for g, (_, ts) in GRUPOS.items()}


def achar(texto: str, regs: dict) -> tuple[list[str], list[str]]:
    """(grupos encontrados, termos encontrados) no texto."""
    t = tx.norm(texto)
    grupos, termos = [], set()
    for g, rs in regs.items():
        ms = [m.group(0).strip() for r in rs for m in r.finditer(t)]
        if ms:
            grupos.append(g)
            termos |= set(ms)
    return grupos, sorted(termos)


def main(argv=None, root=None) -> int:
    root = Path(root or ".")
    regs = compilar()
    desde, ate = comum.periodo(root)
    atores = comum.ler_json(root / "data/config/atores.json")["atores"]
    nome = {a["id"]: a["nome"] for a in atores}
    interno = os.environ.get("ATLAS_INTERNO_DIR") or os.environ.get("ODI_INTERNO_DIR")
    interno = Path(interno) if interno and Path(interno).is_dir() else None
    destino = root / "data/casos"
    destino.mkdir(parents=True, exist_ok=True)
    anterior = json.loads((destino / "brasil.json").read_text(encoding="utf-8")) if (destino / "brasil.json").exists() else {}
    agora = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    fontes, itens = {}, []
    matriz = defaultdict(lambda: defaultdict(lambda: {"lidos": 0, "citam": 0}))
    meses = defaultdict(Counter)
    por_grupo = defaultdict(Counter)

    def registrar(fonte, ator, quando, grupos):
        matriz[ator][fonte]["lidos"] += 1
        if grupos:
            matriz[ator][fonte]["citam"] += 1
            meses[(quando or "")[:7]][fonte] += 1
            for g in grupos:
                por_grupo[g][fonte] += 1

    # 1) publicações dos perfis (todas públicas: autoria dos próprios perfis monitorados)
    for rede, rot in REDES.items():
        ac = comum.ler_acervo(root / "data" / rede / "posts.csv.gz")
        lidos = citam = 0
        for r in ac.values():
            if not (desde <= (r["publicado_em"] or "")[:10] <= (ate or "9999")):
                continue
            g, t = achar(r["texto"], regs)
            lidos += 1
            registrar(rede, r["ator_id"], r["publicado_em"], g)
            if g:
                citam += 1
                itens.append({"fonte": rede, "fonte_rotulo": rot, "ator_id": r["ator_id"], "ator": nome.get(r["ator_id"], r["ator_id"]), "perfil": r["perfil"],
                              "publicado_em": r["publicado_em"], "url": r["url"], "grupos": g, "termos": t,
                              "visualizacoes": r.get("visualizacoes") or None, "texto": " ".join((r["texto"] or "").split())[:600]})
        fontes[rede] = {"rotulo": f"{rot} · publicações", "lidos": lidos, "citam": citam, "universo_nota": "publicações dos perfis lidas no período (ver caderno Panorama)", "lido_em": agora}

    # 2) sites oficiais: título (público) e, com o privado, texto integral
    arts = {}
    f = root / "data/sites/artigos.csv.gz"
    if f.exists():
        with gzip.open(f, "rt", encoding="utf-8", newline="") as h:
            arts = {r["artigo_id"]: r for r in csv.DictReader(h, delimiter=";")}
    textos = {}
    if interno:
        for arq in sorted(glob.glob(str(interno / "sites" / "*.jsonl.gz"))):
            with gzip.open(arq, "rt", encoding="utf-8") as h:
                for ln in h:
                    x = json.loads(ln)
                    textos[str(x.get("artigo_id"))] = " ".join(str(x.get(k) or "") for k in ("titulo", "resumo", "texto"))
    lidos = citam = so_titulo = 0
    for aid, r in arts.items():
        if not (desde <= (r["publicado_em"] or "")[:10] <= (ate or "9999")):
            continue
        integral = textos.get(str(aid))
        g, t = achar(integral if integral else r["titulo"], regs)
        lidos += 1
        so_titulo += 0 if integral else 1
        registrar("sites", r["ator_id"], r["publicado_em"], g)
        if g:
            citam += 1
            itens.append({"fonte": "sites", "fonte_rotulo": "Site oficial", "ator_id": r["ator_id"], "ator": nome.get(r["ator_id"], r["ator_id"]), "perfil": r["site_id"],
                          "publicado_em": r["publicado_em"], "url": r["url"], "grupos": g, "termos": t, "visualizacoes": None,
                          "texto": r["titulo"], "lido_no": "texto integral (repositório privado)" if integral else "só o título"})
    fontes["sites"] = {"rotulo": "Sites oficiais · artigos", "lidos": lidos, "citam": citam, "lido_em": agora,
                       "universo_nota": f"artigos do período; {lidos - so_titulo} lidos no texto integral, {so_titulo} só pelo título" + ("" if interno else " (⛔ sem o repositório privado nesta execução)")}

    # 3) comentários do YouTube: só contagens
    fc = interno / "youtube/comentarios/comentarios.csv.gz" if interno else None
    if fc and fc.exists():
        lidos = citam = 0
        with gzip.open(fc, "rt", encoding="utf-8", newline="") as h:
            for r in csv.DictReader(h, delimiter=";"):
                g, _ = achar(r.get("texto") or "", regs)
                lidos += 1
                registrar("comentarios_youtube", r["ator_id"], r.get("publicado_em"), g)
                citam += bool(g)
        fontes["comentarios_youtube"] = {"rotulo": "YouTube · comentários do público", "lidos": lidos, "citam": citam, "lido_em": agora,
                                         "universo_nota": "todos os comentários e respostas dos vídeos do acervo; texto e autor só no repositório privado"}
    elif (anterior.get("fontes") or {}).get("comentarios_youtube"):
        fontes["comentarios_youtube"] = {**anterior["fontes"]["comentarios_youtube"], "aviso": "repetido da leitura anterior: sem repositório privado nesta execução"}
        for a, fs in (anterior.get("matriz") or {}).items():
            if "comentarios_youtube" in fs:
                matriz[a]["comentarios_youtube"] = fs["comentarios_youtube"]
        for m, fs in (anterior.get("por_mes") or {}).items():
            meses[m]["comentarios_youtube"] = fs.get("comentarios_youtube", 0)
        for gk, fs in (anterior.get("por_grupo") or {}).items():
            por_grupo[gk]["comentarios_youtube"] = fs.get("comentarios_youtube", 0)
    else:
        fontes["comentarios_youtube"] = {"rotulo": "YouTube · comentários do público", "lidos": None, "citam": None, "universo_nota": "⛔ não lido: sem repositório privado"}

    itens.sort(key=lambda x: x["publicado_em"] or "", reverse=True)
    out = {"schema_version": 1, "gerado_em_utc": agora, "titulo": "Brasil, Lula e a família Bolsonaro nas fontes do Atlas",
           "periodo": {"desde": desde, "ate": ate},
           "metodo": ("Regra por palavra, sem inteligência artificial, sobre o texto normalizado (minúsculas, sem acento). Grupos: "
                      + "; ".join(f"{rot}: {', '.join(ts)}" for rot, ts in GRUPOS.values())
                      + ". O asterisco casa por prefixo (brasil* inclui brasileño e Brasilia). 'Flávio Bolsonaro' também conta em 'Família Bolsonaro'. "
                        "A etiqueta diz que o texto cita, não se a citação é favorável ou crítica. Comentários: só contagens, nenhum texto ou autor."),
           "grupos": {g: rot for g, (rot, _) in GRUPOS.items()}, "fontes": fontes,
           "atores": {a["id"]: a["nome"] for a in atores},
           "matriz": {a: dict(fs) for a, fs in matriz.items()},
           "por_mes": {m: dict(c) for m, c in sorted(meses.items()) if m},
           "por_grupo": {g: dict(c) for g, c in por_grupo.items()},
           "itens": itens}
    (destino / "brasil.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(destino / "brasil_itens.csv", "w", encoding="utf-8", newline="") as h:
        w = csv.writer(h, delimiter=";", lineterminator="\n")
        w.writerow(["fonte", "ator", "perfil", "publicado_em", "grupos", "termos_encontrados", "url", "texto_ou_titulo"])
        for x in itens:
            w.writerow([x["fonte_rotulo"], x["ator"], x["perfil"], x["publicado_em"], ", ".join(out["grupos"][g] for g in x["grupos"]), ", ".join(x["termos"]), x["url"], x["texto"]])
    print("caso Brasil: " + " · ".join(f"{v['rotulo']}: {v['citam'] if v.get('citam') is not None else '⛔'} de {v['lidos'] if v.get('lidos') is not None else '⛔'}" for v in fontes.values()))
    print("por grupo: " + " · ".join(f"{GRUPOS[g][0]} {sum(c.values())}" for g, c in por_grupo.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
