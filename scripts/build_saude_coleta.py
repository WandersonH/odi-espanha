#!/usr/bin/env python3
"""Saúde da coleta: para cada série que o Atlas atualiza sozinho, quando foi o último DADO REAL (não a última tentativa).

Porta do build_saude_coleta.py do ODI Atlas ("como posso acreditar que tudo está sendo coletado"): lê só arquivos
publicados (o manifesto mais recente e o histórico manifesto-*.json de cada pasta) e marca ⛔ a série que passou do
prazo de data/config/saude_coleta.json. Uma execução só conta como dado real se terminou "ok" ou "parcial".

Duas situações não são atraso e aparecem com nome próprio:
- inativa: a coleta diária da série ainda não tem teto de gasto autorizado em data/config/coleta.json;
- encerrada: a data final do período (data/config/projeto.json) já passou.

Saída: data/saude_coleta.json (lida pela página). Com --falhar, sai com código 1 se houver série atrasada: o workflow
fica vermelho e o GitHub avisa o responsável por e-mail.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comum  # noqa: E402

OK = ("ok", "parcial")
UTC = dt.timezone.utc


def instante(s) -> dt.datetime | None:
    try:
        return dt.datetime.fromisoformat(str(s).replace("Z", "+00:00")).astimezone(UTC)
    except (TypeError, ValueError):
        return None


def autorizada(geral: dict, s: dict) -> bool:
    bloco = geral["perfis"]["diario"] if s["serie"] == "perfis" else geral["redes"][s["serie"]]["diario"]
    return float(bloco.get("teto_dia_usd") or 0) > 0 and float(bloco.get("teto_mes_usd") or 0) > 0


def main(argv=None, root=None, agora: dt.datetime | None = None) -> int:
    argv, root = list(argv or []), Path(root or ".")
    agora = agora or dt.datetime.now(UTC)
    cfg = comum.ler_json(root / "data/config/saude_coleta.json")
    geral = comum.ler_json(root / "data/config/coleta.json")
    _, ate = comum.periodo(root)
    encerrado = bool(ate and agora.date().isoformat() > ate)
    series, atrasadas = [], []
    for s in cfg["series"]:
        pasta = root / s["pasta"]
        mans = [m for m in comum.manifestos(pasta) if not s.get("modos") or m.get("modo") in s["modos"]]
        ult = mans[-1] if mans else None
        bons = [instante(m.get("run_started_utc")) for m in mans if str(m.get("status", "")).lower().startswith(OK)]
        bons = [t for t in bons if t]
        dado = max(bons) if bons else None
        horas = round((agora - dado).total_seconds() / 3600, 1) if dado else None
        if encerrado:
            sit = "encerrada (período terminou em " + ate + ")"
        elif not autorizada(geral, s):
            sit = "inativa (coleta diária sem teto autorizado)"
        elif dado is None:
            sit = "⛔ nunca coletou"
        elif horas > s["max_horas"]:
            sit = f"⛔ atrasada ({horas} h sem dado novo; prazo {s['max_horas']} h)"
        else:
            sit = "em dia"
        if sit.startswith("⛔"):
            atrasadas.append(f"{s['nome']}: {sit[2:]}")
        series.append({"nome": s["nome"], "serie": s["serie"], "situacao": sit, "max_horas": s["max_horas"],
                       "ultimo_dado": dado.strftime("%Y-%m-%dT%H:%M:%SZ") if dado else None, "horas_desde_ultimo_dado": horas,
                       "ultima_execucao": (ult or {}).get("run_started_utc"), "status_ultima_execucao": str((ult or {}).get("status") or "—")[:200]})
    out = {"verificado_em_utc": agora.strftime("%Y-%m-%dT%H:%M:%SZ"), "nota": cfg.get("nota", ""), "series": series,
           "em_dia": sum(1 for x in series if x["situacao"] == "em dia"), "atrasadas": atrasadas}
    (root / "data/saude_coleta.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for x in series:
        print(f"{x['situacao']} · {x['nome']} · último dado: {x['ultimo_dado'] or '—'}")
    return 1 if "--falhar" in argv and atrasadas else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
