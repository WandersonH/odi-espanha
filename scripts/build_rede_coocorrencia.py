#!/usr/bin/env python3
"""Rede de coocorrência de palavras e #tags por rede social — método do ODI Atlas (scripts/build_rede.py), para seis atores.

Entrada: data/<rede>/posts.csv.gz (acervo) e data/config/atores.json.
Saída por rede: data/<rede>/rede.json (desenhada no caderno "O que dizem"), rede.gexf (Gephi, com posição, cor, tamanho e
comunidade), rede_nos.csv e rede_arestas.csv (Gephi: Laboratório de dados → Importar planilha) e rede_publicacoes_termos.csv
(que termos da rede cada publicação contém: permite refazer a contagem de qualquer aresta).

Método (o mesmo texto útil de "O que dizem": sem links, sem trecho repetido do perfil, sem o nome do próprio ator):
  - nó = palavra (sem acento, sem palavras funcionais) ou #tag; entra se aparece em MIN_PUBS+ publicações, até MAX_NOS nós;
  - aresta = os dois termos aparecem na mesma publicação; peso = nº de publicações em comum, mínimo MIN_PESO;
    cada nó guarda só as TOP_ARESTAS arestas mais fortes (evita o "novelo");
  - comunidades: Louvain (networkx, semente fixa); posição: ForceAtlas2 LinLog (networkx, semente fixa);
  - ator dominante = ator com mais publicações que usam o termo; 'dominancia' = fração dessas publicações.
Diferença do original: lá eram dois lados (Lula × Flávio) e a cor era um gradiente; aqui são seis atores e a cor é a do ator dominante.
Tudo determinístico: a mesma entrada gera a mesma rede.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import math
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

import networkx as nx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comum  # noqa: E402
import texto as tx  # noqa: E402

MIN_PUBS, MAX_NOS, MIN_PESO, TOP_ARESTAS, SEMENTE, MIN_PUBLICACOES_REDE = 8, 150, 3, 8, 42, 30
CORES_COM = ["#165ebd", "#b4472b", "#2f7d5b", "#7a4fb0", "#a8741a", "#3d6f8e", "#c0457a", "#5c7a1f", "#8a5a44", "#2b8a8a"]  # uma cor por comunidade
COR = ["#165ebd", "#b4472b", "#2f7d5b", "#7a4fb0", "#a8741a", "#3d6f8e"]  # mesma ordem de cores da página


def termos_da_pub(r: dict, padrao, excluir: set) -> set[str]:
    util = tx.texto_util(r, padrao)
    palavras = {t for t in tx.termos(util, excluir) if " " not in t}
    tags = {"#" + tx.tag_key(t) for t in tx.HASHTAG.findall(r["texto"] or "")} - {"#" + e for e in excluir}
    return palavras | tags


def montar(pubs: list[tuple[str, set]], ids: list[str], min_pubs=MIN_PUBS, max_nos=MAX_NOS, min_peso=MIN_PESO, top=TOP_ARESTAS) -> nx.Graph:
    df, por = Counter(), {a: Counter() for a in ids}
    for a, ts in pubs:
        df.update(ts)
        por[a].update(ts)
    nos = [t for t, n in sorted(df.items(), key=lambda x: (-x[1], x[0])) if n >= min_pubs][:max_nos]
    sel, co = set(nos), Counter()
    for _, ts in pubs:
        for a, b in combinations(sorted(ts & sel), 2):
            co[(a, b)] += 1
    g = nx.Graph()
    for t in nos:
        uso = {a: por[a][t] for a in ids if por[a][t]}
        dom = max(uso, key=lambda a: (uso[a], -ids.index(a)))
        g.add_node(t, pubs=df[t], uso=uso, dominante=dom, dominancia=round(uso[dom] / df[t], 3))
    viz: dict[str, list] = {t: [] for t in nos}
    for (a, b), w in co.items():
        if w >= min_peso:
            viz[a].append((w, b))
            viz[b].append((w, a))
    for t, lst in viz.items():
        for w, u in sorted(lst, key=lambda x: (-x[0], x[1]))[:top]:
            g.add_edge(t, u, weight=w)
    g.remove_nodes_from([n for n in list(g.nodes) if g.degree(n) == 0])
    return g


def analisar(g: nx.Graph) -> dict:
    if g.number_of_nodes() == 0:
        return {}
    comms = sorted(nx.community.louvain_communities(g, weight="weight", seed=SEMENTE), key=lambda c: (-len(c), sorted(c)[0]))
    for i, c in enumerate(comms):
        for n in c:
            g.nodes[n]["comunidade"] = i
    btw = nx.betweenness_centrality(g, seed=SEMENTE)
    if hasattr(nx, "forceatlas2_layout"):
        inicio = nx.spring_layout(g, weight="weight", seed=SEMENTE)
        pos = nx.forceatlas2_layout(g, pos=inicio, weight="weight", seed=SEMENTE, max_iter=800, scaling_ratio=2.0, linlog=True,
                                    strong_gravity=False, distributed_action=False, gravity=1.0)  # sem 'dissuade hubs': os termos mais ligados ficam no centro
        layout = "ForceAtlas2 LinLog (networkx), sem dissuade hubs"
    else:
        pos = nx.spring_layout(g, weight="weight", seed=SEMENTE, iterations=300)
        layout = "Fruchterman-Reingold (networkx spring_layout)"
    if any(not (math.isfinite(float(p[0])) and math.isfinite(float(p[1]))) for p in pos.values()):
        raise RuntimeError("layout gerou posição inválida (NaN); rede não publicada")
    xs, ys = [p[0] for p in pos.values()], [p[1] for p in pos.values()]
    span = max(max(xs) - min(xs), max(ys) - min(ys)) or 1
    for n, (x, y) in pos.items():
        g.nodes[n].update(x=round(float(x - min(xs)) / float(span) * 1000, 1), y=round(float(y - min(ys)) / float(span) * 1000, 1),
                          intermediacao=round(float(btw[n]), 4), grau=g.degree(n))
    return {"comunidades": comms, "layout": layout, "modularidade": round(nx.community.modularity(g, comms, weight="weight"), 3)}


def construir(root: Path, rede: str, atores: list[dict]) -> str:
    rows = list(comum.ler_acervo(root / "data" / rede / "posts.csv.gz").values())
    pasta = root / "data" / rede
    if len(rows) < MIN_PUBLICACOES_REDE:
        return f"{rede}: ⛔ {len(rows)} publicações, rede não gerada (mínimo {MIN_PUBLICACOES_REDE})"
    padrao, nomes = tx.texto_padrao(rows), {a["id"]: a["nome"] for a in atores}
    ids = [a["id"] for a in atores if any(r["ator_id"] == a["id"] for r in rows)]
    pubs, refs = [], []
    for r in sorted(rows, key=lambda r: (r["ator_id"], r["publicado_em"], r["post_id"])):
        nome = tx.norm(nomes.get(r["ator_id"], "")).split()
        excluir = set(nome) | {"".join(nome)} | {tx.tag_key(r["perfil"])}
        pubs.append((r["ator_id"], termos_da_pub(r, padrao, excluir)))
        refs.append(r)
    g = montar(pubs, ids)
    info = analisar(g)
    cor = {a: COR[i % len(COR)] for i, a in enumerate([a["id"] for a in atores])}
    metodo = (f"Rede de coocorrência: nó = palavra ou #tag presente em {MIN_PUBS}+ publicações (até {MAX_NOS}); aresta = aparecem na mesma "
              f"publicação (peso = nº de publicações, mínimo {MIN_PESO}; até {TOP_ARESTAS} arestas mais fortes por nó). Comunidades: Louvain; "
              f"posição: {info.get('layout', '—')}; semente {SEMENTE}. Texto sem links, sem trechos repetidos do perfil e sem o nome do próprio ator. "
              "Cor = comunidade (Louvain), como nas redes dos casos; o ator que mais usa cada termo está na tabela e na ficha do nó. Método do ODI Atlas (build_rede.py), adaptado de dois lados para seis atores.")
    comms = info.get("comunidades", [])
    out = {"schema_version": 1, "gerado_em_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "rede": rede, "metodo": metodo,
           "networkx": nx.__version__, "publicacoes": {a: sum(1 for x, _ in pubs if x == a) for a in ids}, "atores": {a: {"nome": nomes[a], "cor": cor[a]} for a in ids},
           "nos_total": g.number_of_nodes(), "arestas_total": g.number_of_edges(), "modularidade": info.get("modularidade"),
           "comunidades": [{"id": i, "nos": len(c), "principais": sorted(c, key=lambda n: (-g.nodes[n]["pubs"], n))[:8],
                            "ator_mais_presente": Counter({a: sum(g.nodes[n]["uso"].get(a, 0) for n in c) for a in ids}).most_common(1)[0][0]} for i, c in enumerate(comms)],
           "nos": [{"id": n, "x": d["x"], "y": d["y"], "v": d["pubs"], "u": d["uso"], "d": d["dominante"], "dm": d["dominancia"], "c": d["comunidade"],
                    "g": d["grau"], "b": d["intermediacao"]} for n, d in sorted(g.nodes(data=True))],
           "arestas": [[a, b, d["weight"]] for a, b, d in sorted(g.edges(data=True))]}
    (pasta / "rede.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    with open(pasta / "rede_nos.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["Id", "Label", "publicacoes", "ator_dominante", "dominancia", *[f"pubs_{a}" for a in ids], "comunidade", "grau", "intermediacao", "x", "y"])
        for n in out["nos"]:
            w.writerow([n["id"], n["id"], n["v"], nomes[n["d"]], n["dm"], *[n["u"].get(a, 0) for a in ids], n["c"] + 1, n["g"], n["b"], n["x"], n["y"]])
    with open(pasta / "rede_arestas.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["Source", "Target", "Weight", "Type"])
        w.writerows([a, b, p, "Undirected"] for a, b, p in out["arestas"])
    nos_set = set(g.nodes)
    with open(pasta / "rede_publicacoes_termos.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["ator", "perfil", "post_id", "url", "termos_na_rede"])
        for (a, ts), r in zip(pubs, refs):
            if ts & nos_set:
                w.writerow([nomes[a], r["perfil"], r["post_id"], r["url"], "|".join(sorted(ts & nos_set))])
    gx = nx.Graph()
    for n, d in g.nodes(data=True):
        c = CORES_COM[d["comunidade"] % len(CORES_COM)]
        gx.add_node(n, label=n, publicacoes=d["pubs"], ator_dominante=nomes[d["dominante"]], dominancia=d["dominancia"], comunidade=d["comunidade"] + 1,
                    grau=d["grau"], intermediacao=d["intermediacao"],
                    viz={"position": {"x": d["x"], "y": -d["y"], "z": 0.0}, "size": round(2 + 3 * d["pubs"] ** 0.5, 2),
                         "color": {"r": int(c[1:3], 16), "g": int(c[3:5], 16), "b": int(c[5:7], 16), "a": 1.0}})
    gx.add_edges_from((a, b, {"weight": p}) for a, b, p in out["arestas"])
    gx.graph["descricao"] = metodo
    nx.write_gexf(gx, pasta / "rede.gexf")
    linhas = [f"{rede}: {g.number_of_nodes()} nós, {g.number_of_edges()} arestas, {len(comms)} comunidades, modularidade {info.get('modularidade')}, {info.get('layout')}"]
    linhas += [f"  C{c['id'] + 1} ({c['nos']} nós, mais presente: {nomes[c['ator_mais_presente']]}): {', '.join(c['principais'])}" for c in out["comunidades"][:6]]
    return "\n".join(linhas)


def main(argv=None, root=None) -> int:
    root = Path(root or ".")
    atores = comum.ler_json(root / "data/config/atores.json")["atores"]
    for rede in comum.REDES:
        print(construir(root, rede, atores))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
