#!/usr/bin/env python3
"""Comentários do YouTube dos vídeos do acervo — leitura completa pela API oficial, sem custo.

Mesmo método de scripts/collect_comentarios_youtube_completo.py do ODI Atlas: commentThreads.list (do mais novo para o
mais antigo, 100 por página) até o fim de cada vídeo e, para as conversas com mais respostas do que as que vêm junto,
comments.list (100 por página). 1 unidade de cota por chamada; o teto de chamadas por execução fica em
data/config/comentarios.json e a leitura continua, na execução seguinte, nos vídeos que faltaram.

Comentário é dado de terceiros: texto e autor ficam SÓ no repositório privado (youtube/comentarios/). Sem o privado,
nada é lido. Ao público vai apenas data/youtube/comentarios/cobertura.json: contagens (universo informado pela
plataforma × quanto foi lido), sem texto, sem nome e sem canal de autor.
"""
from __future__ import annotations

import csv
import datetime as dt
import gzip
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.parse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comum  # noqa: E402
from net import get_json, now_utc  # noqa: E402

API = "https://www.googleapis.com/youtube/v3"
CCOLS = ["comentario_id", "video_id", "ator_id", "resposta_a", "autor", "autor_canal_id", "texto", "curtidas",
         "publicado_em", "atualizado_em", "respostas", "coletado_em"]
FONTE_UNIVERSO = "soma do contador de comentários de cada vídeo (YouTube Data API, videos.list → statistics.commentCount; inclui respostas)"


class ErroAPI(Exception):
    def __init__(self, motivo: str):
        super().__init__(motivo)
        self.motivo = motivo


class SemCota(Exception):
    """Teto de chamadas desta execução atingido."""


class Cota:
    """Teto de chamadas desta execução, compartilhado entre as leituras em paralelo."""

    def __init__(self, n: int):
        self.resta, self.usadas, self.parar, self._trava = n, 0, False, threading.Lock()

    def gastar(self) -> bool:
        with self._trava:
            if self.parar or self.resta <= 0:
                return False
            self.resta, self.usadas = self.resta - 1, self.usadas + 1
            return True


def chamar_api(chave: str):
    def buscar(recurso: str, params: dict) -> dict:
        url = f"{API}/{recurso}?" + urllib.parse.urlencode({**params, "key": chave})
        for tent in range(3):
            try:
                return get_json(url, timeout=60)
            except urllib.error.HTTPError as e:
                try:
                    motivo = (json.loads(e.read()).get("error", {}).get("errors") or [{}])[0].get("reason") or str(e.code)
                except Exception:  # noqa: BLE001
                    motivo = str(e.code)
                if e.code in (500, 503) and tent < 2:
                    time.sleep(2 * (tent + 1))
                    continue
                raise ErroAPI(motivo) from None  # sem o erro original: o endereço leva a chave
            except Exception as e:  # noqa: BLE001
                if tent < 2:
                    time.sleep(2 * (tent + 1))
                    continue
                raise ErroAPI(type(e).__name__) from None
        raise ErroAPI("sem resposta")
    return buscar


def linha(c: dict, video_id: str, ator_id: str, agora: str, respostas="") -> dict:
    s = c.get("snippet") or {}
    return {"comentario_id": c.get("id", ""), "video_id": video_id, "ator_id": ator_id, "resposta_a": s.get("parentId", ""),
            "autor": s.get("authorDisplayName", ""), "autor_canal_id": (s.get("authorChannelId") or {}).get("value", ""),
            "texto": s.get("textOriginal") or s.get("textDisplay") or "", "curtidas": s.get("likeCount", ""),
            "publicado_em": s.get("publishedAt", ""), "atualizado_em": s.get("updatedAt", ""), "respostas": respostas, "coletado_em": agora}


def ler_video(buscar, vid: str, ator_id: str, agora: str, cota: Cota) -> tuple[list[dict], dict]:
    """Todas as conversas e respostas de um vídeo. Devolve (linhas, estado); estado['completo'] só quando a paginação chegou ao fim."""
    linhas, pendentes, est = [], [], {"completo": False}

    def paginas(recurso: str, params: dict):
        tok = None
        while True:
            if not cota.gastar():
                raise SemCota
            d = buscar(recurso, {**params, **({"pageToken": tok} if tok else {})})
            yield d.get("items") or []
            tok = d.get("nextPageToken")
            if not tok:
                return
    try:
        for itens in paginas("commentThreads", {"part": "snippet,replies", "videoId": vid, "maxResults": 100, "order": "time", "textFormat": "plainText"}):
            for it in itens:
                s = it.get("snippet") or {}
                top, n = s.get("topLevelComment") or {}, int(s.get("totalReplyCount") or 0)
                linhas.append(linha(top, vid, ator_id, agora, n))
                vindas = (it.get("replies") or {}).get("comments") or []
                if n > len(vindas) and top.get("id"):
                    pendentes.append(top["id"])  # a API só manda até 5 respostas junto: as demais são lidas à parte
                else:
                    linhas += [linha(r, vid, ator_id, agora) for r in vindas]
        for pid in pendentes:
            for itens in paginas("comments", {"part": "snippet", "parentId": pid, "maxResults": 100, "textFormat": "plainText"}):
                linhas += [linha(r, vid, ator_id, agora) for r in itens]
        est["completo"] = True
    except SemCota:  # teto de chamadas desta execução: o vídeo fica para a próxima
        est["parou"] = "teto de chamadas desta execução"
    except ErroAPI as e:
        if e.motivo == "commentsDisabled":
            est.update(completo=True, desativados=True)
        elif e.motivo == "videoNotFound":
            est.update(completo=True, indisponivel=True)
        else:
            est["erro"] = e.motivo
    return linhas, est


def main(argv=None, buscar=None, root=None, hoje=None) -> int:
    root = Path(root or ".")
    agora, hoje = now_utc(), hoje or comum.hoje_brt()
    cfg = json.loads((root / "data/config/comentarios.json").read_text(encoding="utf-8"))["youtube"]
    pasta = root / "data/youtube/comentarios"
    pasta.mkdir(parents=True, exist_ok=True)
    out = {"schema_version": 1, "gerado_em_utc": agora, "fonte": "YouTube Data API v3 (commentThreads.list e comments.list)",
           "nota": cfg["nota"], "universo_fonte": FONTE_UNIVERSO, "atores": {}}

    def fim(status: str, code: int) -> int:
        out["status"] = status
        (pasta / "cobertura.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"comentários do youtube: {status}")
        return code

    interno = os.environ.get("ATLAS_INTERNO_DIR") or os.environ.get("ODI_INTERNO_DIR")
    if not interno:
        return fim("⛔ repositório privado indisponível: comentário é dado de terceiros e não é lido sem ele", 1)
    chave = "" if buscar else os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not chave and not buscar:
        return fim("⛔ YOUTUBE_API_KEY ausente", 1)
    buscar = buscar or chamar_api(chave)
    videos = sorted(comum.ler_acervo(root / "data/youtube/posts.csv.gz").values(), key=lambda v: v["publicado_em"], reverse=True)
    if not videos:
        return fim("⛔ nenhum vídeo no acervo (rode a coleta do YouTube antes)", 1)

    d = Path(interno) / "youtube/comentarios"
    d.mkdir(parents=True, exist_ok=True)
    estado = json.loads((d / "estado.json").read_text(encoding="utf-8")) if (d / "estado.json").exists() else {}
    guardados: dict[str, dict] = {}
    if (d / "comentarios.csv.gz").exists():
        with gzip.open(d / "comentarios.csv.gz", "rt", encoding="utf-8", newline="") as f:
            guardados = {r["comentario_id"]: r for r in csv.DictReader(f, delimiter=";")}

    recente = (hoje - dt.timedelta(days=int(cfg["reler_videos_dos_ultimos_dias"]))).isoformat()
    fila = []
    for v in videos:
        e = estado.get(v["post_id"]) or {}
        if str(v["comentarios"]) == "0" and not e.get("completo"):  # contador zero: nada a ler, sem gastar chamada
            estado[v["post_id"]] = {"completo": True, "lidos": 0, "contador": "0", "lido_em": agora}
        elif not e.get("completo") or ((v["publicado_em"] or "")[:10] >= recente and str(e.get("contador")) != str(v["comentarios"])):
            fila.append(v)
    fila.sort(key=lambda v: bool((estado.get(v["post_id"]) or {}).get("completo")))  # primeiro os que nunca foram lidos por inteiro
    cota = Cota(int(cfg["chamadas_por_execucao"]))

    def um(v):
        return (v, *ler_video(buscar, v["post_id"], v["ator_id"], agora, cota))
    novos = 0
    with ThreadPoolExecutor(max_workers=int(cfg.get("paralelo") or 4)) as ex:
        for v, linhas, e in ex.map(um, fila):
            for r in linhas:
                if r["comentario_id"]:
                    novos += r["comentario_id"] not in guardados
                    guardados[r["comentario_id"]] = r
            if e.get("erro") == "quotaExceeded":
                cota.parar = True  # cota diária da API esgotada: para tudo e continua amanhã
            if e.get("completo") or not (estado.get(v["post_id"]) or {}).get("completo"):
                estado[v["post_id"]] = {**e, "lidos": len(linhas), "contador": v["comentarios"], "lido_em": agora}

    with gzip.open(d / "comentarios.csv.gz", "wt", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, CCOLS, delimiter=";", lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(guardados.values(), key=lambda r: (r["video_id"], r["publicado_em"], r["comentario_id"])))
    (d / "estado.json").write_text(json.dumps(estado, ensure_ascii=False, indent=1), encoding="utf-8")

    por_video, resp_video, autores, meses = Counter(), Counter(), {}, {}
    for r in guardados.values():
        por_video[r["video_id"]] += 1
        resp_video[r["video_id"]] += bool(r["resposta_a"])
        autores.setdefault(r["ator_id"], set()).add(r["autor_canal_id"] or r["autor"])
        meses.setdefault(r["ator_id"], Counter())[(r["publicado_em"] or "")[:7]] += 1
    nomes = {p["ator_id"]: p["ator_nome"] for p in comum.perfis_da_rede(root, "youtube")[0]}
    faltam = 0
    for a in sorted({v["ator_id"] for v in videos}):
        vs = [v for v in videos if v["ator_id"] == a]
        com = [v for v in vs if v["comentarios"] not in ("", None)]
        est = [estado.get(v["post_id"]) or {} for v in vs]
        completos = sum(1 for e in est if e.get("completo"))
        faltam += len(vs) - completos
        erros = Counter(e["erro"] for e in est if e.get("erro") and not e.get("completo"))
        out["atores"][a] = {
            "nome": nomes.get(a, a), "videos": len(vs), "videos_com_contador": len(com),
            "universo_comentarios": sum(comum.inteiro(v["comentarios"]) or 0 for v in com) if com else None,
            "videos_lidos_por_inteiro": completos, "videos_com_comentarios_desativados": sum(1 for e in est if e.get("desativados")),
            "comentarios_lidos": sum(por_video[v["post_id"]] for v in vs), "dos_quais_respostas": sum(resp_video[v["post_id"]] for v in vs),
            "autores_distintos": len(autores.get(a, ())), "por_mes": dict(sorted(meses.get(a, {}).items())), "erros": dict(erros),
            "cobertura": "completa: todas as páginas de todos os vídeos foram lidas até o fim" if completos == len(vs)
                         else f"parcial ⛔: {len(vs) - completos} de {len(vs)} vídeos ainda sem leitura completa"}
        o = out["atores"][a]
        print(f"{o['nome']}: universo {o['universo_comentarios']} (em {len(com)} de {len(vs)} vídeos) · lidos {o['comentarios_lidos']} "
              f"({o['dos_quais_respostas']} respostas) · vídeos lidos por inteiro {completos}/{len(vs)} · {o['cobertura']}{' · erros ' + str(dict(erros)) if erros else ''}")
    out.update(chamadas_nesta_execucao=cota.usadas, comentarios_novos_nesta_execucao=novos, comentarios_guardados=len(guardados))
    print(f"chamadas à API nesta execução: {cota.usadas} (teto {cfg['chamadas_por_execucao']}) · comentários novos {novos} · guardados no privado {len(guardados)}")
    return fim("ok" if not faltam else f"⚠️ parcial: {faltam} vídeos ainda sem leitura completa (continua na próxima execução)", 0 if guardados or not faltam else 1)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
