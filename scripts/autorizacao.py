#!/usr/bin/env python3
"""Diz se há teto de gasto autorizado em data/config/coleta.json, para os workflows não rodarem (nem falharem) à toa.

Sem argumentos: imprime `diario=sim|nao` (alguma série com diário autorizado), no formato de $GITHUB_OUTPUT.
Com `<serie> <modo>` (serie: instagram, x, facebook ou perfis; modo: teste, carga, diario ou sonda): sai com 0 se
aquele modo tem teto maior que zero, 1 se não tem.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def autorizado(cfg: dict, serie: str, modo: str) -> bool:
    bloco = (cfg["perfis"] if serie == "perfis" else cfg["redes"][serie]).get(modo) or {}
    if modo == "diario":
        return float(bloco.get("teto_dia_usd") or 0) > 0 and float(bloco.get("teto_mes_usd") or 0) > 0
    return float(bloco.get("teto_usd") or 0) > 0


def main(argv) -> int:
    cfg = json.loads(Path("data/config/coleta.json").read_text(encoding="utf-8"))
    if len(argv) == 2:
        return 0 if autorizado(cfg, argv[0], argv[1]) else 1
    alguma = any(autorizado(cfg, s, "diario") for s in list(cfg["redes"]) + ["perfis"])
    print(f"diario={'sim' if alguma else 'nao'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
