#!/usr/bin/env python3
"""Regras de texto do caderno "O que dizem", portadas de scripts/build_conteudo.py do ODI Atlas (mesmo método):
normalização (minúsculas, sem acento), dicionário aberto de temas por regras (termo com * casa por prefixo),
descarte de trechos repetidos em 10+ publicações do mesmo perfil, nuvem por nº de publicações (não de ocorrências) e
hashtags. O que muda é a língua: as palavras vazias são as do espanhol. Classificação por regras, NÃO por IA:
auditável e replicável, mas não entende ironia nem contexto.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter

URL = re.compile(r"(https?://\S+|www\.\S+)", re.I)
SEG = re.compile(r"(?<=[.!?])\s+|\s[|•]\s|\s-\s|\s—\s|\s*[\U0001F300-\U0001FAFF☀-➿]+\s*|\n")  # emojis também separam trechos
LIMIAR_REPETICAO = 10   # trecho presente em 10+ publicações do mesmo perfil = texto padrão (rodapé, institucional)
NUVEM_TOP, NUVEM_MIN = 60, 3
HASHTAG = re.compile(r"#([0-9A-Za-zÀ-ÿ_]{3,})")


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", URL.sub(" ", s or "")).lower()
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " " + re.sub(r"[^a-z0-9#]+", " ", s).strip() + " "


STOP = set(norm("""a al algo alguna algunas alguno algunos ante antes aqui asi aun aunque bien cada casi como con contra cual cuales
cuando de del desde donde dos durante e el ella ellas ello ellos en entre era eran es esa esas ese eso esos esta estaba estamos estan
estar estas este esto estos fue fueron ha habia hace hacer han hasta hay he hemos hoy la las le les lo los mas me mi mientras mis
mismo mucho muy nada ni no nos nosotros nuestra nuestras nuestro nuestros o os otra otras otro otros para pero poco por porque
puede pueden que quien quienes se sea sean ser si sido siempre sin sobre solo son su sus tal tambien tan tanto te tener tiene tienen
toda todas todo todos tras tu tus un una uno unos va vamos van ver vez y ya yo usted ustedes les del al
ano anos dia dias hora horas ayer manana semana lunes martes miercoles jueves viernes sabado domingo enero febrero marzo abril
mayo junio julio agosto septiembre octubre noviembre diciembre
video directo canal youtube instagram facebook twitter suscribete sigue siguenos enlace link via traves aqui""").split())


def term_regex(t: str) -> re.Pattern:
    """Termo do dicionário → expressão sobre o texto normalizado. 'inmigra*' casa por prefixo; '#' antes é aceito."""
    n = norm(t.rstrip("*")).strip()
    return re.compile(r"(?<=[ #])" + re.escape(n).replace(r"\ ", " ") + (r"[a-z0-9]*" if t.endswith("*") else "") + r"(?= )")


def segmentos(texto: str) -> list[str]:
    return [s.strip() for s in SEG.split(URL.sub(" ", texto or "")) if s and len(s.strip()) >= 12]


def texto_padrao(pubs: list[dict]) -> dict[str, set]:
    """Por perfil, os trechos repetidos em LIMIAR_REPETICAO ou mais publicações."""
    cont: dict[str, Counter] = {}
    for r in pubs:
        cont.setdefault(r["perfil"], Counter()).update(set(segmentos(r["texto"])))
    return {p: {s for s, n in c.items() if n >= LIMIAR_REPETICAO} for p, c in cont.items()}


def texto_util(r: dict, padrao: dict[str, set]) -> str:
    fora = padrao.get(r["perfil"], set())
    segs = segmentos(r["texto"])
    return " ".join(s for s in segs if s not in fora) if segs else (r["texto"] or "")


def termos(texto: str, excluir: set) -> set:
    """Palavras e pares de palavras vizinhas (sem palavras vazias, números e os nomes do próprio ator)."""
    ok = lambda t: len(t) >= 3 and t not in STOP and t not in excluir and not t.isdigit()  # noqa: E731
    toks = [t for t in norm(texto).split() if not t.startswith("#")]
    return {t for t in toks if ok(t)} | {f"{a} {b}" for a, b in zip(toks, toks[1:]) if ok(a) and ok(b)}


def nuvem(textos: list[str], excluir: set, top: int = NUVEM_TOP, minimo: int = NUVEM_MIN) -> list[list]:
    df = Counter()
    for tx in textos:
        df.update(termos(tx, excluir))
    df = {t: n for t, n in df.items() if n >= minimo}
    for t, n in list(df.items()):  # o par absorve a palavra solta quando cobre 80%+ das ocorrências dela
        if " " in t:
            for w in t.split():
                if w in df and n >= 0.8 * df[w]:
                    df.pop(w, None)
    return [[t, n] for t, n in sorted(df.items(), key=lambda x: (-x[1], x[0]))[:top]]


def tag_key(t: str) -> str:
    return norm(t).replace(" ", "").lstrip("#")


def compilar(cfg: dict):
    temas = {k: [term_regex(t) for t in v] for k, v in cfg["temas"].items()}
    return temas, [term_regex(t) for t in cfg["adversarios"]], [term_regex(t) for t in cfg["pede_voto"]]


def classificar(texto: str, temas, adv, voto) -> dict:
    t = norm(texto)
    achados = [k for k, regs in temas.items() if any(r.search(t) for r in regs)]
    return {"temas": achados or ["sem_tema"], "cita_adversario": any(r.search(t) for r in adv), "pede_voto": any(r.search(t) for r in voto)}
