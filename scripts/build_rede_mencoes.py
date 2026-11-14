#!/usr/bin/env python3
"""Rede de menções: quem os perfis monitorados marcam (@) nos próprios posts, no Instagram e no X.

Entrada: data/instagram/posts.csv.gz e data/x/posts.csv.gz. Saída (data/redes/):
  mencoes.gexf                         Gephi (rede dirigida, com peso)
  mencoes_nos.csv / mencoes_arestas.csv  "Importar planilha" do Gephi e NodeXL
  mencoes_posts.csv                    base de conferência: cada menção com o link do post
  mencoes.json                         lida pela página

Rede dirigida: perfil monitorado → conta marcada; peso = nº de posts com a marcação. É a rede de SAÍDA (quem eles
citam), não a de entrada (quem fala deles). Cada rede tem o seu espaço de nomes: o nó é "<rede>:<conta>", porque a
mesma conta pode ter donos diferentes no Instagram e no X. O Facebook fica fora: lá a marcação não aparece como
@conta no texto do post. Uma comunidade desta rede não é, sozinha, uma "bolha" (regra de leitura do ODI Atlas).
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comum  # noqa: E402
from net import now_utc  # noqa: E402

RE_ARROBA = re.compile(r"(?<![\w@./])@([A-Za-z0-9_](?:[A-Za-z0-9_.]{0,28}[A-Za-z0-9_])?)")
REDES = ("instagram", "x")


def main(argv=None, root=None) -> int:
    root = Path(root or ".")
    monitorados = {}  # nó → (ator, rótulo)
    for rede in REDES:
        conf, _ = comum.perfis_da_rede(root, rede)
        for p in conf:
            monitorados[f"{rede}:{p['perfil'].lower()}"] = (p["ator_nome"], p["perfil"])
    arestas, base = Counter(), []
    for rede in REDES:
        for r in comum.ler_acervo(root / "data" / rede / "posts.csv.gz").values():
            origem = f"{rede}:{r['perfil'].lower()}"
            for a in sorted({a.lower() for a in RE_ARROBA.findall(r["texto"])} - {r["perfil"].lower()}):
                arestas[(origem, f"{rede}:{a}")] += 1
                base.append({"rede": rede, "perfil": r["perfil"], "marcado": a, "publicado_em": r["publicado_em"], "url": r["url"]})
    if not arestas:
        print("rede de menções: ⛔ nenhum post com marcação no acervo, nada exportado")
        return 0
    grau_e = Counter()
    for (_, d), w in arestas.items():
        grau_e[d] += w
    nos = sorted({n for par in arestas for n in par} | {o for o, _ in arestas})
    ficha = lambda n: {"id": n, "label": "@" + n.split(":", 1)[1], "rede": n.split(":", 1)[0],  # noqa: E731
                       "papel": "monitorado" if n in monitorados else "marcado", "ator": (monitorados.get(n) or ("", ""))[0], "posts_que_o_marcam": grau_e.get(n, 0)}
    saida = root / "data/redes"
    saida.mkdir(parents=True, exist_ok=True)
    with open(saida / "mencoes_nos.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, ["id", "label", "rede", "papel", "ator", "posts_que_o_marcam"], delimiter=";", lineterminator="\n")
        w.writeheader()
        w.writerows(ficha(n) for n in nos)
    with open(saida / "mencoes_arestas.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";", lineterminator="\n")
        w.writerow(["source", "target", "type", "weight"])
        w.writerows([o, d, "Directed", n] for (o, d), n in sorted(arestas.items(), key=lambda kv: (-kv[1], kv[0])))
    with open(saida / "mencoes_posts.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, ["rede", "perfil", "marcado", "publicado_em", "url"], delimiter=";", lineterminator="\n")
        w.writeheader()
        w.writerows(sorted(base, key=lambda b: (b["rede"], b["perfil"], b["publicado_em"])))
    x = ['<?xml version="1.0" encoding="UTF-8"?>', '<gexf xmlns="http://gexf.net/1.3" version="1.3">',
         f'<meta lastmodifieddate="{now_utc()[:10]}"><creator>ODI Espanha · build_rede_mencoes.py</creator><description>Perfil monitorado → conta marcada; peso = posts com a marcação</description></meta>',
         '<graph mode="static" defaultedgetype="directed">',
         '<attributes class="node"><attribute id="0" title="rede" type="string"/><attribute id="1" title="papel" type="string"/><attribute id="2" title="ator" type="string"/><attribute id="3" title="posts_que_o_marcam" type="integer"/></attributes>',
         "<nodes>"]
    for n in nos:
        fi = ficha(n)
        x.append(f'<node id={quoteattr(n)} label={quoteattr(fi["label"])}><attvalues><attvalue for="0" value={quoteattr(fi["rede"])}/><attvalue for="1" value={quoteattr(fi["papel"])}/>'
                 f'<attvalue for="2" value={quoteattr(fi["ator"])}/><attvalue for="3" value="{fi["posts_que_o_marcam"]}"/></attvalues></node>')
    x.append("</nodes><edges>")
    for i, ((o, d), n) in enumerate(sorted(arestas.items())):
        x.append(f'<edge id="{i}" source={quoteattr(o)} target={quoteattr(d)} weight="{n}"/>')
    x.append("</edges></graph></gexf>")
    (saida / "mencoes.gexf").write_text("\n".join(x) + "\n", encoding="utf-8")
    (saida / "mencoes.json").write_text(json.dumps({
        "gerado_em_utc": now_utc(), "nos": len(nos), "arestas": len(arestas), "posts_com_marcacao": len({b["url"] for b in base}),
        "leitura": "Rede de saída: perfil monitorado → conta marcada; peso = nº de posts. Instagram e X; Facebook fora.",
        "maiores": [{"de": o, "para": d, "posts": n} for (o, d), n in arestas.most_common(40)]}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"rede de menções: {len(nos)} nós · {len(arestas)} arestas · {escape(str(len(base)))} marcações")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
