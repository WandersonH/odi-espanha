#!/usr/bin/env python3
"""Vídeos dos canais de YouTube confirmados em data/config/atores.json, no período de data/config/projeto.json.

API oficial do YouTube (Data API v3), sem Apify e sem custo; a chave vem só do segredo YOUTUBE_API_KEY e nunca é
impressa. Para cada canal: channels.list (canal, lista de envios, total de vídeos e inscritos), playlistItems.list
(lista de envios, do mais recente para trás, até a data inicial) e videos.list (título, descrição, duração e números).

Universo: o YouTube informa o total de vídeos públicos do canal (toda a vida do canal). A lista de envios é exaustiva
e ordenada por data, então ler até a data inicial cobre o período inteiro; a cobertura só sai "completa" quando a
leitura chegou de fato a um vídeo anterior ao período ou ao fim da lista. Cada execução relê o período todo: os
números de cada vídeo ficam com a data da última leitura.

Saída: data/youtube/posts.csv.gz (mesmas colunas das outras redes; texto = título — descrição),
data/youtube/manifesto-*.json e data/perfis/youtube_latest.csv (inscritos e total de vídeos por canal).
"""
from __future__ import annotations

import csv
import os
import re
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comum  # noqa: E402
from apify import erro_curto  # noqa: E402
from comum import g, inteiro  # noqa: E402
from net import get_json, now_utc  # noqa: E402

REDE = "youtube"
API = "https://www.googleapis.com/youtube/v3"
MAX_PAGINAS = 400  # 20.000 vídeos por canal


def alvo(pf: dict) -> dict:
    """Como pedir o canal à API, pelo formato do endereço: /channel/UC…, /@nome ou /user/nome."""
    u, p = pf.get("url") or "", pf["perfil"]
    m = re.search(r"/channel/(UC[\w-]+)", u)
    if m or p.startswith("UC"):
        return {"id": m.group(1) if m else p}
    m = re.search(r"/@([\w.-]+)", u)
    if m or p.startswith("@"):
        return {"forHandle": "@" + (m.group(1) if m else p.lstrip("@"))}
    m = re.search(r"/user/([\w.-]+)", u)
    return {"forUsername": m.group(1) if m else p}


def duracao(iso) -> int | str:
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", str(iso or ""))
    return "" if not m or not any(m.groups()) else sum(int(v or 0) * k for v, k in zip(m.groups(), (86400, 3600, 60, 1)))


def linha(v: dict, pf: dict, agora: str) -> dict:
    s, st = v.get("snippet") or {}, v.get("statistics") or {}
    texto = " — ".join(x for x in (" ".join(str(s.get("title") or "").split()), " ".join(str(s.get("description") or "").split())) if x)
    return {"ator_id": pf["ator_id"], "ator_nome": pf["ator_nome"], "rede": REDE, "perfil": pf["perfil"], "post_id": v["id"],
            "url": f"https://www.youtube.com/watch?v={v['id']}", "publicado_em": comum.quando(s.get("publishedAt")), "texto": texto,
            "tipo": "vídeo", "duracao_s": duracao(g(v, "contentDetails.duration")), "visualizacoes": inteiro(st.get("viewCount")),
            "curtidas": inteiro(st.get("likeCount")), "comentarios": inteiro(st.get("commentCount")), "compartilhamentos": "",
            "primeira_coleta": agora, "ultima_coleta": agora, "capa_url": g(s, "thumbnails.high.url", "thumbnails.default.url") or ""}


def main(argv=None, buscar=None, root=None, hoje=None) -> int:
    root = Path(root or ".")
    hoje = hoje or comum.hoje_brt()
    desde, ate = comum.periodo(root)
    pasta, agora = root / "data" / REDE, now_utc()
    conf, fora = comum.perfis_da_rede(root, REDE)
    man = {"run_started_utc": agora, "rede": REDE, "ferramenta": "YouTube Data API v3 (channels, playlistItems, videos)", "modo": "carga",
           "periodo": {"desde": desde, "ate": ate}, "desde_leitura": desde, "custo_usd": 0.0, "perfis": [],
           "perfis_fora_da_coleta": [{"ator_id": p["ator_id"], "perfil": p["perfil"], "motivo": "candidato a conferir" if p["perfil"] else (p["nota"] or "não localizado")} for p in fora]}

    def fim(status: str, code: int) -> int:
        man["status"] = status
        comum.gravar_manifesto(pasta, man)
        print(f"youtube: {status}")
        return code

    if not conf:
        return fim("⛔ nenhum canal confirmado (data/config/atores.json)", 1)
    chave = "" if buscar else os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not buscar and not chave:
        return fim("⛔ YOUTUBE_API_KEY ausente (cadastre o segredo no GitHub)", 1)
    buscar = buscar or (lambda recurso, params: get_json(f"{API}/{recurso}?{urllib.parse.urlencode({**params, 'key': chave})}", timeout=60))

    acervo = comum.ler_acervo(pasta / "posts.csv.gz")
    novos_total, mudou, universo = 0, False, []
    for pf in conf:
        reg = {"ator_id": pf["ator_id"], "ator_nome": pf["ator_nome"], "perfil": pf["perfil"], "pedido": "lista de envios até a data inicial"}
        man["perfis"].append(reg)
        try:
            canal = ((buscar("channels", {"part": "snippet,contentDetails,statistics", **alvo(pf)}) or {}).get("items") or [None])[0]
            if not canal:
                raise LookupError("canal não encontrado pela API")
            est = canal.get("statistics") or {}
            reg["universo"] = {"posts_total_plataforma": inteiro(est.get("videoCount")) if est.get("videoCount") is not None else None,
                               "posts_total_nota": "videoCount: vídeos públicos de toda a vida do canal",
                               "seguidores": None if est.get("hiddenSubscriberCount") or est.get("subscriberCount") is None else inteiro(est.get("subscriberCount")),
                               "nome_exibido": g(canal, "snippet.title") or "", "canal_id": canal.get("id"),
                               "posts_no_periodo_plataforma": None, "posts_no_periodo_nota": "⛔ o YouTube não informa o total por período; a lista de envios lida até a data inicial cobre o período"}
            ids, tok, chegou, paginas, listados = [], None, False, 0, 0
            while paginas < MAX_PAGINAS:
                pg = buscar("playlistItems", {"part": "contentDetails", "playlistId": g(canal, "contentDetails.relatedPlaylists.uploads"), "maxResults": 50, **({"pageToken": tok} if tok else {})}) or {}
                paginas += 1
                datas = [(g(i, "contentDetails.videoId"), (g(i, "contentDetails.videoPublishedAt") or "")[:10]) for i in pg.get("items") or []]
                listados += len(datas)
                ids += [v for v, d in datas if v and d >= desde and not (ate and d > ate)]
                tok = pg.get("nextPageToken")
                if not tok or (datas and all(d and d < desde for _, d in datas)):
                    chegou = True  # fim da lista ou página inteira anterior ao período
                    break
            lidos = novos = 0
            todas = []
            for i in range(0, len(ids), 50):
                for v in (buscar("videos", {"part": "snippet,statistics,contentDetails", "id": ",".join(ids[i:i + 50])}) or {}).get("items") or []:
                    r = linha(v, pf, agora)
                    dia = r["publicado_em"][:10]
                    if len(dia) != 10 or dia < desde or (ate and dia > ate):
                        continue
                    old = acervo.get(r["post_id"]) or {}
                    r["primeira_coleta"] = old.get("primeira_coleta") or agora
                    novos += 0 if old else 1
                    acervo[r["post_id"]] = r
                    todas.append(r["publicado_em"])
                    lidos, mudou = lidos + 1, True
            reg.update(itens=listados, posts_do_perfil=len(ids), lidos_no_periodo=lidos, novos=novos, indisponiveis=len(ids) - lidos,
                       mais_antigo=min(todas, default=None), mais_recente=max(todas, default=None), erro=None,
                       cobertura="completa: a lista de envios do canal foi lida até a data inicial" if chegou else f"parcial ⛔: a leitura parou em {MAX_PAGINAS} páginas da lista de envios")
            novos_total += novos
            u = reg["universo"]
            universo.append({"ator_id": pf["ator_id"], "ator_nome": pf["ator_nome"], "rede": REDE, "perfil": pf["perfil"], "url": pf["url"], "nome_exibido": u["nome_exibido"],
                             "seguidores": "" if u["seguidores"] is None else u["seguidores"], "posts_total": "" if u["posts_total_plataforma"] is None else u["posts_total_plataforma"],
                             "verificado": "", "captured_at": agora[:10], "fonte": "YouTube Data API (channels.list, statistics)"})
        except Exception as e:  # noqa: BLE001 — a chave vai na URL do pedido, nunca na mensagem
            reg.update(itens=0, lidos_no_periodo=0, novos=0, cobertura="⛔ não lido", erro=erro_curto(e) if not isinstance(e, LookupError) else str(e))
        print(f"{pf['ator_nome']} · {pf['perfil']}: {reg.get('lidos_no_periodo')} vídeos no período · universo {(reg.get('universo') or {}).get('posts_total_plataforma')} · {reg['cobertura']}{' · ' + reg['erro'] if reg['erro'] else ''}")

    if mudou:
        comum.gravar_acervo(pasta / "posts.csv.gz", acervo)
    if universo:
        d = root / "data/perfis"
        d.mkdir(parents=True, exist_ok=True)
        for nome in (f"youtube_{agora[:10]}.csv", "youtube_latest.csv"):
            with open(d / nome, "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, comum.PCOLS, delimiter=";", lineterminator="\n")
                w.writeheader()
                w.writerows(universo)
    man.update(posts_novos=novos_total, posts_no_acervo=len(acervo))
    com_erro = [r for r in man["perfis"] if r.get("erro")]
    parciais = [r for r in man["perfis"] if str(r.get("cobertura", "")).startswith("parcial")]
    if len(com_erro) == len(man["perfis"]):
        return fim(f"⛔ nenhum canal lido: {com_erro[0]['erro']}", 1)
    if com_erro or parciais:
        return fim(f"parcial: {len(com_erro)} canal(is) com erro, {len(parciais)} com leitura no limite", 0)
    return fim("ok", 0)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
