#!/usr/bin/env python3
"""Posts públicos das páginas de Facebook confirmadas em data/config/atores.json, no período de data/config/projeto.json.

Porta do collect_facebook_posts.py do ODI Atlas (ator apify/facebook-posts-scraper, sem login). Limites conhecidos do
ator, registrados no Atlas: não aceita data final (lê do mais recente para trás até a data inicial) e para perto de
1.000 posts por página (700 com filtro de data). Página que chega a esse número sai marcada como parcial ⛔.
O Facebook não informa quantos posts a página tem: o universo desta rede é ⛔ desconhecido.

Uso: --teste | --carga | --diario (ver scripts/comum.py). Saída: data/facebook/posts.csv.gz e manifesto-*.json.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comum  # noqa: E402
from comum import g, inteiro, quando  # noqa: E402

REDE = "facebook"


def pedido(cfg: dict, pf: dict, n: int, desde: str, ate, hoje) -> dict:
    return {"startUrls": [{"url": pf["url"]}], "resultsLimit": n, "onlyPostsNewerThan": desde}


def e_post(x: dict, pf: dict, cfg: dict) -> bool:
    return isinstance(x, dict) and not x.get("error") and bool(g(x, "postId", "id", "post_id"))


def linha(x: dict, pf: dict, agora: str) -> dict:
    midia = x.get("media") if isinstance(x.get("media"), list) else []
    capa = g(x, "thumbnail", "full_picture", "image") or next((g(m, "thumbnail", "photo_image.uri", "image.uri") for m in midia if isinstance(m, dict)), "")
    video = g(x, "viewsCount", "videoViewCount") is not None or bool(g(x, "isVideo"))
    return {"ator_id": pf["ator_id"], "ator_nome": pf["ator_nome"], "rede": REDE, "perfil": pf["perfil"],
            "post_id": str(g(x, "postId", "id", "post_id") or ""), "url": g(x, "url", "postUrl", "facebookUrl") or "",
            "publicado_em": quando(g(x, "time", "timestamp", "date", "createdAt")),
            "texto": " ".join(str(g(x, "text", "message", "postText") or "").split()), "tipo": "vídeo" if video else "post",
            "duracao_s": "", "visualizacoes": inteiro(g(x, "viewsCount", "videoViewCount", "views")),
            "curtidas": inteiro(g(x, "likes", "reactionsCount", "topReactionsCount", "reactions")),  # no Facebook, curtidas = reações
            "comentarios": inteiro(g(x, "comments", "commentsCount")), "compartilhamentos": inteiro(g(x, "shares", "sharesCount")),
            "primeira_coleta": agora, "ultima_coleta": agora, "capa_url": capa or ""}


def main(argv=None, executar=None, root=None, hoje=None) -> int:
    return comum.rodar(REDE, sys.modules[__name__], argv, executar, root, hoje)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
