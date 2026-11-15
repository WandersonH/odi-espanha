#!/usr/bin/env python3
"""Planilha de conferência da etiqueta 'cita o Brasil': toda publicação do acervo que cita o Brasil, Lula ou a família
Bolsonaro, com os termos encontrados. Lê data/<rede>/conteudo.json (gerado por build_o_que_dizem.py) e grava
data/site/cita_brasil.csv e data/site/cita_brasil.json (contagem por ator e rede). Só publicações dos perfis monitorados."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comum  # noqa: E402

COLS = ["ator", "rede", "perfil", "publicado_em", "termos_encontrados", "url", "visualizacoes", "curtidas", "texto"]


def main(argv=None, root=None) -> int:
    root = Path(root or ".")
    linhas, resumo = [], {}
    for rede in comum.REDES:
        f = root / "data" / rede / "conteudo.json"
        if not f.exists():
            continue
        for aid, a in json.loads(f.read_text(encoding="utf-8")).get("atores", {}).items():
            ps = [p for p in a["publicacoes"] if p.get("cita_brasil")]
            resumo.setdefault(aid, {"nome": a["nome"], "redes": {}})["redes"][rede] = {"publicacoes": a["total_publicacoes"], "citam_o_brasil": len(ps)}
            linhas += [{"ator": a["nome"], "rede": rede, "perfil": p["perfil"], "publicado_em": p["publicado_em"], "termos_encontrados": ", ".join(p.get("brasil_termos") or []),
                        "url": p["url"], "visualizacoes": "" if p.get("visualizacoes") is None else p["visualizacoes"], "curtidas": "" if p.get("curtidas") is None else p["curtidas"],
                        "texto": " ".join((p.get("texto") or "").split())} for p in ps]
    pasta = root / "data/site"
    pasta.mkdir(parents=True, exist_ok=True)
    with open(pasta / "cita_brasil.csv", "w", encoding="utf-8", newline="") as h:
        w = csv.DictWriter(h, COLS, delimiter=";", lineterminator="\n")
        w.writeheader()
        w.writerows(sorted(linhas, key=lambda r: (r["ator"], r["publicado_em"]), reverse=True))
    (pasta / "cita_brasil.json").write_text(json.dumps({"total": len(linhas), "atores": resumo}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"cita o Brasil: {len(linhas)} publicações · " + " · ".join(f"{v['nome']} {sum(r['citam_o_brasil'] for r in v['redes'].values())}" for v in resumo.values()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
