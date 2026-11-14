#!/usr/bin/env python3
"""Posts públicos dos perfis de Instagram confirmados em data/config/atores.json, no período de data/config/projeto.json.

Porta do collect_instagram_posts.py do ODI Atlas: mesmos atores e mesmos pedidos (o primeiro ator de coleta.json é o
esdrasdw/instagram-content-scraper; os pedidos dos outros três atores testados no Atlas continuam aqui para troca rápida).
Uma leitura por perfil para os posts e, no esdrasdw, uma segunda no modo reels só para as visualizações.

Uso: --teste | --carga | --diario (ver scripts/comum.py). Saída: data/instagram/posts.csv.gz e manifesto-*.json.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comum  # noqa: E402
from comum import g, inteiro, quando  # noqa: E402

REDE = "instagram"


def pedido(cfg: dict, pf: dict, n: int, desde: str, ate, hoje) -> dict:
    ator, perfil = cfg["ator"], pf["perfil"]
    if ator.startswith("esdrasdw~"):  # legenda completa é opcional (selectedFields); visualizações só no modo reels
        return {"directUrls": [perfil], "resultsType": "posts", "resultsLimit": n, "onlyPostsNewerThan": desde,
                "selectedFields": ["shortCode", "id", "url", "timestamp", "caption", "title", "likesCount", "commentsCount",
                                   "displayUrl", "ownerUsername", "videoDuration", "type"]}
    if ator.startswith("apidojo~"):
        return {"startUrls": [f"https://www.instagram.com/{perfil}/"], "maxItems": n, "until": desde}
    if ator.startswith("apify~instagram-post-scraper"):
        return {"username": [perfil], "resultsLimit": n, "onlyPostsNewerThan": desde}
    return {"directUrls": [f"https://www.instagram.com/{perfil}/"], "resultsType": "posts", "resultsLimit": n, "onlyPostsNewerThan": desde}


def complemento(cfg: dict, pf: dict, n: int, desde: str) -> dict | None:
    """2ª leitura só para visualizações (o esdrasdw só informa plays no modo reels)."""
    if cfg["ator"].startswith("esdrasdw~"):
        return {"directUrls": [pf["perfil"]], "resultsType": "reels", "resultsLimit": n, "onlyPostsNewerThan": desde,
                "selectedFields": ["shortCode", "videoPlayCount", "videoDuration"]}
    return None


def unir(itens: list, vistos: list) -> None:
    plays = {str(v.get("shortCode")): v for v in vistos if isinstance(v, dict) and v.get("shortCode")}
    for x in itens:
        v = plays.get(str(x.get("shortCode")))
        if v:
            x["videoPlayCount"], x["_reel"] = v.get("videoPlayCount"), True
            x["videoDuration"] = x.get("videoDuration") or v.get("videoDuration")


def e_post(x: dict, pf: dict, cfg: dict) -> bool:
    if not isinstance(x, dict) or x.get("error") or x.get("demo") or not g(x, "shortCode", "shortcode", "code", "id"):
        return False
    dono = str(g(x, "ownerUsername", "owner.username") or "").lower()
    return not dono or dono == pf["perfil"].lower()  # post de outro perfil (colaboração devolvida pelo ator) fica fora


def linha(x: dict, pf: dict, agora: str) -> dict:
    sc = str(g(x, "shortCode", "shortcode", "code") or "")
    tipo = str(g(x, "type", "productType", "media_type") or "")
    views = inteiro(g(x, "videoPlayCount", "videoViewCount", "playCount", "viewCount", "video_view_count"))
    likes = inteiro(g(x, "likesCount", "likeCount", "like_count"))
    return {"ator_id": pf["ator_id"], "ator_nome": pf["ator_nome"], "rede": REDE, "perfil": pf["perfil"],
            "post_id": sc or str(g(x, "id", "pk") or ""), "url": g(x, "url", "postUrl") or (f"https://www.instagram.com/p/{sc}/" if sc else ""),
            "publicado_em": quando(g(x, "timestamp", "takenAt", "taken_at", "createdAt")),
            "texto": " ".join(str(g(x, "caption", "caption.text", "text", "title") or "").split()),
            "tipo": "vídeo" if views != "" or x.get("_reel") or re.search(r"video|reel|clip", tipo, re.I) else "post",
            "duracao_s": inteiro(g(x, "videoDuration", "video_duration")), "visualizacoes": views,
            "curtidas": likes if likes != "" and likes >= 0 else "",  # o Instagram devolve -1 quando o perfil oculta as curtidas
            "comentarios": inteiro(g(x, "commentsCount", "commentCount", "comment_count")),
            "compartilhamentos": inteiro(g(x, "reshareCount", "sharesCount")),
            "primeira_coleta": agora, "ultima_coleta": agora,
            "capa_url": g(x, "displayUrl", "thumbnailUrl", "imageUrl") or ""}


def main(argv=None, executar=None, root=None, hoje=None) -> int:
    return comum.rodar(REDE, sys.modules[__name__], argv, executar, root, hoje)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
