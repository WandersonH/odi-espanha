#!/usr/bin/env python3
"""Carga do corpus na área do pesquisador (Supabase, tabela public.corpus).

Adaptado de scripts/carregar_area_pesquisador.py do ODI Atlas (mesmo banco, mesma página). Aqui o "caso" é o ator
monitorado (id de data/config/atores.json). Entram:
  - publicações dos perfis monitorados: data/<rede>/posts.csv.gz (acervo público) → fonte 'post', autor = perfil monitorado;
  - comentários do YouTube: $ATLAS_INTERNO_DIR/youtube/comentarios/comentarios.csv.gz (privado) → fonte 'comentario'.

Proteções: comentário NUNCA leva autor nem canal do autor; nenhum link ou id de conta comum é enviado.
Triagem automática (ofensivo/ódio): os modelos do ODI Atlas são para português; aqui os campos vão vazios (null).
A chave de serviço vem SÓ do ambiente (secret SUPABASE_SERVICE_ROLE_KEY_ESP no GitHub; nunca no código).

Uso: ATLAS_INTERNO_DIR=… SUPABASE_URL=… SUPABASE_SERVICE_ROLE_KEY=… python scripts/carregar_area_pesquisador.py [--caso vox] [--seco]
  --seco: não envia nada; só conta o que seria enviado.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comum  # noqa: E402

LOTE, LIMITE_MB = 500, 420  # limite de segurança abaixo dos 500 MB do plano gratuito do Supabase
VAR = re.compile("[︎️]")
try:
    import emoji as _emoji
except ImportError:  # sem a biblioteca (testes locais): faixas Unicode mais comuns
    _emoji = None
_FAIXA = re.compile("[\U0001F1E6-\U0001F1FF\U0001F300-\U0001FAFF☀-➿⭐⭕]")


def emojis_de(t: str) -> list[str]:
    if _emoji:
        return sorted({VAR.sub("", e["emoji"]) for e in _emoji.emoji_list(t)})
    return sorted(set(_FAIXA.findall(t)))


def linhas(root: Path, interno: Path | None, so_caso: str | None = None):
    """Uma linha de public.corpus por texto. Publicações do acervo público e, havendo o privado, comentários do YouTube."""
    def base(caso, rede, fonte, item, data, texto, autor=None, candidato=None):
        return {"caso": caso, "rede": rede, "fonte": fonte, "item_id": item, "publicado_em": data or None, "autor": autor,
                "texto": texto, "emojis": emojis_de(texto), "candidato": candidato, "ofensivo": None, "odio": None}
    for rede in comum.REDES:
        f = root / "data" / rede / "posts.csv.gz"
        if not f.exists():
            continue
        for r in comum.ler_acervo(f).values():
            t = (r.get("texto") or "").strip()
            if not t or not r.get("post_id") or (so_caso and r["ator_id"] != so_caso):
                continue
            autor = r.get("ator_nome") if rede == "youtube" else (f"@{r['perfil']}" if r.get("perfil") else None)
            yield base(r["ator_id"], rede, "post", r["post_id"], r.get("publicado_em"), t, autor=autor)
    f = interno / "youtube/comentarios/comentarios.csv.gz" if interno else None
    if f and f.exists():
        with gzip.open(f, "rt", encoding="utf-8", newline="") as h:
            for r in csv.DictReader(h, delimiter=";"):
                t = (r.get("texto") or "").strip()
                if not t or not r.get("comentario_id") or (so_caso and r["ator_id"] != so_caso):
                    continue
                yield base(r["ator_id"], "youtube", "comentario", r["comentario_id"], r.get("publicado_em"), t, candidato=r["ator_id"])


def _post(url: str, chave: str, caminho: str, corpo: bytes, extra: dict | None = None, timeout: int = 120) -> bytes:
    req = urllib.request.Request(f"{url}{caminho}", data=corpo, method="POST",
                                 headers={"apikey": chave, "Authorization": f"Bearer {chave}", "Content-Type": "application/json", **(extra or {})})
    return urllib.request.urlopen(req, timeout=timeout).read()


def enviar(url: str, chave: str, lote: list[dict]) -> None:
    corpo = json.dumps(lote).encode()
    for tent in range(4):
        try:
            _post(url, chave, "/rest/v1/corpus?on_conflict=caso,fonte,item_id", corpo, {"Prefer": "resolution=merge-duplicates,return=minimal"})
            return
        except urllib.error.HTTPError as e:
            if e.code < 500 or tent == 3:
                raise RuntimeError(f"envio recusado (HTTP {e.code})") from None  # sem o erro original: não repetir cabeçalhos
        except Exception:  # noqa: BLE001
            if tent == 3:
                raise RuntimeError("envio sem resposta") from None
        time.sleep(3 * (tent + 1))


def tamanho_mb(url: str, chave: str) -> float:
    return float(json.loads(_post(url, chave, "/rest/v1/rpc/tamanho_banco_mb", b"{}")))


def main(argv=None, enviar_fn=None, root=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--caso")
    ap.add_argument("--seco", action="store_true")
    a = ap.parse_args(argv)
    root = Path(root or ".")
    d = os.environ.get("ATLAS_INTERNO_DIR") or os.environ.get("ODI_INTERNO_DIR") or ""
    interno = Path(d) if d and Path(d).is_dir() else None
    url, chave = os.environ.get("SUPABASE_URL", "").rstrip("/"), os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    real = not a.seco and enviar_fn is None
    if real and not (url and chave):
        print("⛔ faltam SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY no ambiente (secret SUPABASE_SERVICE_ROLE_KEY_ESP no GitHub)")
        return 1
    if not interno:
        print("comentários: ⛔ repositório privado indisponível — só as publicações dos perfis entram nesta carga")
    if real:
        try:
            mb = tamanho_mb(url, chave)
        except Exception:  # noqa: BLE001
            print("⛔ o banco não respondeu a tamanho_banco_mb: as migrações de supabase/migrations/ foram aplicadas?")
            return 1
        if mb >= LIMITE_MB:
            print(f"⛔ banco com {mb} MB (limite de segurança {LIMITE_MB} MB): carga não iniciada")
            return 1
    mandar = enviar_fn or (lambda lote: enviar(url, chave, lote))
    lote, vistos, n = [], set(), Counter()
    for r in linhas(root, interno, a.caso):
        k = (r["caso"], r["fonte"], r["item_id"])
        if k in vistos:
            continue
        vistos.add(k)
        n[(r["caso"], r["fonte"])] += 1
        lote.append(r)
        if len(lote) >= LOTE:
            if not a.seco:
                mandar(lote)
            lote = []
    if lote and not a.seco:
        mandar(lote)
    verbo = "contados" if a.seco else "enviados"
    for caso in sorted({c for c, _ in n}):
        print(f"{caso}: {n[(caso, 'post')]} publicações · {n[(caso, 'comentario')]} comentários {verbo}")
    if real:  # depois da carga: amostra de validação, resumo por caso e nuvens preparadas (como no ODI Atlas)
        for fn in ("preparar_area", "atualizar_frequencias"):
            try:
                print(f"{fn}: {_post(url, chave, f'/rest/v1/rpc/{fn}', b'{}', timeout=900).decode()[:300]}")
                break
            except urllib.error.HTTPError as e:
                print(f"⛔ {fn} não rodou (HTTP {e.code})")
    total = sum(n.values())
    print(f"total: {total} textos {verbo}" + (f" · banco com {tamanho_mb(url, chave)} MB" if real else ""))
    return 0 if total else 1


if __name__ == "__main__":
    sys.exit(main())
