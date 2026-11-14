"""Apoio aos testes: monta um projeto temporário com a configuração real e os ajustes pedidos (tetos, perfis, período)."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))


def projeto(tetos: dict | None = None, confirmar: list[tuple[str, str]] | None = None, ate: str | None = None, perfis_teto: dict | None = None) -> Path:
    """Copia data/config para uma pasta temporária. tetos = {rede: {modo: {campo: valor}}}; confirmar = [(ator_id, rede)]."""
    t = Path(tempfile.mkdtemp(prefix="odi-esp-"))
    shutil.copytree(RAIZ / "data/config", t / "data/config")
    c = json.loads((t / "data/config/coleta.json").read_text(encoding="utf-8"))
    for rede, modos in (tetos or {}).items():
        for modo, campos in modos.items():
            c["redes"][rede][modo].update(campos)
        c["redes"][rede]["autorizacao"] = "teste automatizado"
    for modo, campos in (perfis_teto or {}).items():
        c["perfis"][modo].update(campos)
        c["perfis"]["autorizacao"] = "teste automatizado"
    (t / "data/config/coleta.json").write_text(json.dumps(c), encoding="utf-8")
    a = json.loads((t / "data/config/atores.json").read_text(encoding="utf-8"))
    for ator in a["atores"]:
        for rede, pf in ator["perfis"].items():
            if (ator["id"], rede) in (confirmar or []):
                pf["confirmado"] = True
    (t / "data/config/atores.json").write_text(json.dumps(a), encoding="utf-8")
    if ate:
        p = json.loads((t / "data/config/projeto.json").read_text(encoding="utf-8"))
        p["periodo"]["ate"] = ate
        (t / "data/config/projeto.json").write_text(json.dumps(p), encoding="utf-8")
    return t


def manifesto(root: Path, pasta: str) -> dict:
    return json.loads((root / "data" / pasta / "manifesto_latest.json").read_text(encoding="utf-8"))


def tweet(i, autor="vox_es", quando="Wed Sep 02 12:00:00 +0000 2026", texto="texto", **extra):
    return {"type": "tweet", "id": str(i), "text": texto, "createdAt": quando, "likeCount": 10, "replyCount": 2, "retweetCount": 3, "quoteCount": 1,
            "viewCount": 1000, "author": {"userName": autor, "name": "VOX", "followers": 600000, "statusesCount": 90000}, **extra}
