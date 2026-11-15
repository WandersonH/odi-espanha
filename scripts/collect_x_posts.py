#!/usr/bin/env python3
"""Posts públicos dos perfis de X confirmados em data/config/atores.json, no período de data/config/projeto.json.

Porta do collect_x_posts.py do ODI Atlas (ator xquik/x-tweet-scraper: busca do próprio X, from:perfil since:data).
Entram posts, respostas e citações escritos pelo perfil; reposts ficam fora (como no Atlas), salvo se
coleta.json → redes.x.incluir_reposts for true.

Universo: o X informa, em cada post, quantos seguidores e quantas publicações o perfil tem no total (statusesCount, que
soma posts, respostas e reposts de toda a vida da conta). Isso vai para o manifesto e para data/perfis/x_latest.csv.
O total de publicações dentro do período o X não informa.

Uso: --teste | --carga | --diario (ver scripts/comum.py). Saída: data/x/posts.csv.gz e manifesto-*.json.
"""
from __future__ import annotations

import csv
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comum  # noqa: E402
from comum import g, inteiro, quando  # noqa: E402

REDE = "x"


def autor(x: dict) -> str:
    return str(g(x, "author.userName", "author.username", "author.screen_name", "user.screen_name", "user.username", "username") or "")


def e_repost(x: dict) -> bool:
    return bool(g(x, "isRetweet", "retweeted_status", "retweetedTweet")) or str(g(x, "fullText", "text") or "").startswith("RT @")


def pedido(cfg: dict, pf: dict, n: int, desde: str, ate, hoje) -> dict:
    h = pf["perfil"]
    if "xquik" in cfg["ator"]:
        q = f"from:{h} since:{desde}"
        if ate and hoje and ate < hoje.isoformat():  # until: é exclusivo no X
            q += f" until:{(dt.date.fromisoformat(ate) + dt.timedelta(days=1)).isoformat()}"
        if not cfg.get("incluir_reposts"):
            q += " -filter:retweets"
        return {"searchTerms": [q], "maxItems": n, "queryType": "Latest"}
    return {"twitterHandles": [h], "start": desde, "maxItems": n, "sort": "Latest"}


def e_post(x: dict, pf: dict, cfg: dict) -> bool:
    if not isinstance(x, dict) or x.get("noResults") or x.get("error") or not g(x, "id", "id_str", "tweetId"):
        return False
    if str(g(x, "type") or "tweet").lower() not in ("tweet", "post", "reply", "quote", "retweet"):
        return False
    if autor(x).lower() != pf["perfil"].lower():  # a busca pode devolver post de outro perfil
        return False
    return bool(cfg.get("incluir_reposts")) or not e_repost(x)


def linha(x: dict, pf: dict, agora: str) -> dict:
    tid = str(g(x, "id", "id_str", "tweetId") or "")
    rt = inteiro(g(x, "retweetCount", "retweet_count", "public_metrics.retweet_count"))
    qt = inteiro(g(x, "quoteCount", "quote_count", "public_metrics.quote_count"))
    midia = g(x, "extendedEntities.media") or g(x, "entities.media") or []
    capa = next((m.get("media_url_https") for m in midia if isinstance(m, dict) and m.get("media_url_https")), "") if isinstance(midia, list) else ""
    tipo = ("repost" if e_repost(x) else "resposta" if g(x, "isReply", "inReplyToId", "in_reply_to_status_id_str", "inReplyToStatusId")
            else "citação" if g(x, "isQuote", "quotedTweet", "quoted_status", "quoteId") else "post")
    return {"ator_id": pf["ator_id"], "ator_nome": pf["ator_nome"], "rede": REDE, "perfil": pf["perfil"], "post_id": tid,
            "url": g(x, "url", "twitterUrl") or f"https://x.com/{pf['perfil']}/status/{tid}",
            "publicado_em": quando(g(x, "createdAt", "created_at", "date")), "texto": " ".join(str(g(x, "fullText", "text") or "").split()),
            "tipo": tipo, "duracao_s": "", "visualizacoes": inteiro(g(x, "viewCount", "views", "view_count", "public_metrics.impression_count")),
            "curtidas": inteiro(g(x, "likeCount", "favoriteCount", "favorite_count", "public_metrics.like_count")),
            "comentarios": inteiro(g(x, "replyCount", "reply_count", "public_metrics.reply_count")),
            "compartilhamentos": "" if rt == "" and qt == "" else (rt or 0) + (qt or 0),
            "primeira_coleta": agora, "ultima_coleta": agora, "capa_url": capa}


def universo(itens: list, pf: dict) -> dict:
    """O que o X informa sobre o perfil dentro do próprio post. Ausente fica None (nunca estimado)."""
    meus = [x for x in itens if isinstance(x, dict) and autor(x).lower() == pf["perfil"].lower()]
    primeiro = lambda *ks: next((inteiro(g(x, *ks)) for x in meus if g(x, *ks) is not None), "")  # noqa: E731
    seg = primeiro("author.followers", "author.followersCount", "author.followers_count", "user.followers_count", "author.public_metrics.followers_count")
    tot = primeiro("author.statusesCount", "author.statuses_count", "user.statuses_count", "author.public_metrics.tweet_count")
    return {"seguidores": seg if seg != "" else None, "posts_total_plataforma": tot if tot != "" else None,
            "posts_total_nota": "statusesCount do X: posts, respostas e reposts de toda a vida da conta",
            "posts_no_periodo_plataforma": None, "posts_no_periodo_nota": "⛔ o X não informa o total por período",
            "nome_exibido": next((str(g(x, "author.name", "user.name")) for x in meus if g(x, "author.name", "user.name")), "")}


def depois(root: Path, man: dict, conf: list, agora: str) -> None:
    """Seguidores e total de publicações de cada perfil lido → data/perfis/x_latest.csv e x_AAAA-MM-DD.csv."""
    por = {p["perfil"]: p for p in conf}
    linhas = []
    for r in man["perfis"]:
        u, pf = r.get("universo") or {}, por[r["perfil"]]
        if u.get("seguidores") is None and u.get("posts_total_plataforma") is None:
            continue
        linhas.append({"ator_id": pf["ator_id"], "ator_nome": pf["ator_nome"], "rede": REDE, "perfil": pf["perfil"], "url": pf["url"],
                       "nome_exibido": u.get("nome_exibido") or "", "seguidores": "" if u.get("seguidores") is None else u["seguidores"],
                       "posts_total": "" if u.get("posts_total_plataforma") is None else u["posts_total_plataforma"],
                       "verificado": "", "captured_at": agora[:10], "fonte": "campo author do post (Apify · " + man["ferramenta"].split("· ")[-1] + ")"})
    if not linhas:
        return
    d = root / "data/perfis"
    d.mkdir(parents=True, exist_ok=True)
    for nome in (f"x_{agora[:10]}.csv", "x_latest.csv"):
        # Soma ao que já existe: uma leitura só de alguns perfis (--perfis) não pode apagar o número dos outros.
        antes = {}
        if (d / nome).exists():
            with open(d / nome, encoding="utf-8", newline="") as f:
                antes = {r["perfil"].lower(): r for r in csv.DictReader(f, delimiter=";")}
        antes.update({r["perfil"].lower(): r for r in linhas})
        with open(d / nome, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, comum.PCOLS, delimiter=";", lineterminator="\n", extrasaction="ignore")
            w.writeheader()
            w.writerows(sorted(antes.values(), key=lambda r: (r["ator_id"], r["perfil"].lower())))


def main(argv=None, executar=None, root=None, hoje=None) -> int:
    return comum.rodar(REDE, sys.modules[__name__], argv, executar, root, hoje)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
