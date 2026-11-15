#!/usr/bin/env python3
"""Copia para o repositório privado o resultado das execuções da Apify JÁ FEITAS (e já pagas).

Não inicia execução nenhuma e não gasta: só lista as execuções de cada ator usado pelo projeto e baixa o conjunto de
dados de cada uma. Serve para guardar o bruto das coletas feitas quando o repositório privado ainda não aceitava
gravação. Não consulta saldo nem limites da conta. Não toca no acervo público, nos manifestos nem no registro de gasto.

Saída privada (ATLAS_INTERNO_DIR): apify_execucoes/<ator>/<id da execução>.jsonl.gz e apify_execucoes/indice.json.
Saída pública: data/bruto_privado.json — só contagens (execuções e itens guardados, por ator).
"""
from __future__ import annotations

import gzip
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from apify import api, baixar_itens, erro_curto  # noqa: E402
from net import now_utc  # noqa: E402

PADRAO = re.compile(r"\b[a-z0-9][a-z0-9_.-]*~[a-z0-9][a-z0-9_.-]*\b")
FONTES = ("data/config/coleta.json", "data/config/meta_anuncios.json", "scripts/collect_perfis.py")


def atores(root: Path) -> list[str]:
    """Todo ator da Apify citado na configuração e no coletor de perfis (formato usuario~ator)."""
    achados: set[str] = set()
    for f in FONTES:
        if (root / f).exists():
            achados |= set(PADRAO.findall((root / f).read_text(encoding="utf-8")))
    return sorted(achados)


def main(argv=None, listar=None, baixar=None, root=None) -> int:
    root = Path(root or ".")
    geral = json.loads((root / "data/config/coleta.json").read_text(encoding="utf-8"))
    agora = now_utc()
    out = {"gerado_em_utc": agora, "por_ator": {},
           "nota": "Bruto das execuções da Apify já feitas, copiado para o repositório privado sem nova execução e sem custo. "
                   "Aqui ficam só contagens; o conteúdo pode trazer dados de terceiros e não vem ao público."}

    def fim(status: str, code: int) -> int:
        out["status"] = status
        (root / "data").mkdir(exist_ok=True)
        (root / "data/bruto_privado.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"bruto no privado: {status}")
        return code

    interno = os.environ.get("ATLAS_INTERNO_DIR") or os.environ.get("ODI_INTERNO_DIR")
    if not interno:
        return fim("⛔ repositório privado indisponível: nada foi baixado (o bruto não pode ir ao público)", 1)
    token = "" if listar else os.environ.get(geral["segredo"], "").strip()
    if not token and not listar:
        return fim(f"⛔ {geral['segredo']} ausente", 1)
    listar = listar or (lambda ator: api("GET", f"/acts/{ator}/runs?desc=1&limit=200", token)["data"].get("items") or [])
    baixar = baixar or (lambda ds: baixar_itens(token, ds))
    base = Path(interno) / "apify_execucoes"
    base.mkdir(parents=True, exist_ok=True)
    indice = json.loads((base / "indice.json").read_text(encoding="utf-8")) if (base / "indice.json").exists() else {}
    problemas = 0
    for ator in atores(root):
        reg = {"execucoes_encontradas": 0, "gravadas_agora": 0, "ja_gravadas": 0, "itens_gravados_agora": 0, "sem_itens": 0, "falhas": 0}
        out["por_ator"][ator.replace("~", "/")] = reg
        try:
            execs = listar(ator)
        except Exception as e:  # noqa: BLE001 — o token vai no cabeçalho, nunca na mensagem
            reg["erro"], problemas = erro_curto(e), problemas + 1
            print(f"{ator.replace('~', '/')}: ⛔ lista de execuções não lida ({reg['erro']})")
            continue
        for r in execs:
            rid, ds = r.get("id"), r.get("defaultDatasetId")
            if not rid or not ds:
                continue
            reg["execucoes_encontradas"] += 1
            arq = base / ator / f"{rid}.jsonl.gz"
            if arq.exists() or (rid in indice and not indice[rid].get("itens")):
                reg["ja_gravadas"] += 1
                continue
            try:
                itens = baixar(ds)
            except Exception:  # noqa: BLE001
                reg["falhas"], problemas = reg["falhas"] + 1, problemas + 1
                continue
            indice[rid] = {"ator": ator, "iniciada_em": r.get("startedAt"), "terminada_em": r.get("finishedAt"),
                           "status": r.get("status"), "itens": len(itens), "baixada_em": agora}
            if not itens:
                reg["sem_itens"] += 1
                continue
            arq.parent.mkdir(parents=True, exist_ok=True)
            with gzip.open(arq, "wt", encoding="utf-8") as f:
                for x in itens:
                    f.write(json.dumps(x, ensure_ascii=False) + "\n")
            reg["gravadas_agora"] += 1
            reg["itens_gravados_agora"] += len(itens)
        print(f"{ator.replace('~', '/')}: {reg['execucoes_encontradas']} execuções · gravadas agora {reg['gravadas_agora']} ({reg['itens_gravados_agora']} itens) · "
              f"já gravadas {reg['ja_gravadas']} · sem itens {reg['sem_itens']} · falhas {reg['falhas']}")
    (base / "indice.json").write_text(json.dumps(indice, ensure_ascii=False, indent=1), encoding="utf-8")
    tot = sum(r["itens_gravados_agora"] for r in out["por_ator"].values())
    return fim(("ok" if not problemas else "⚠️ parcial") + f" · {tot} itens gravados nesta execução", 0 if not problemas else 1)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
