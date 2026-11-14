#!/usr/bin/env python3
"""Corpus no formato IRaMuTeQ (**** *variáveis), um texto por post, a partir do acervo público.

Saída (data/corpus/):
  odi_espanha_iramuteq.txt   todos os posts com texto
  <rede>_iramuteq.txt        um arquivo por rede
  manifesto.json             quantos posts entraram, quantos ficaram fora por não ter texto, variáveis usadas

Variáveis de cada texto: *ator_<id> *rede_<rede> *mes_<AAAA>_<MM> *tipo_<tipo>. Limpeza mínima e declarada: saem os
endereços (http...), o asterisco (marcador de variável no IRaMuTeQ) e as quebras de linha; # e @ ficam como palavra
(hashtag_x, arroba_x) para não se perderem na lematização. Os textos estão em espanhol: no IRaMuTeQ, escolher o
dicionário espanhol. Nenhum texto é reescrito, traduzido ou resumido.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comum  # noqa: E402
from net import now_utc  # noqa: E402

RE_URL = re.compile(r"https?://\S+|www\.\S+")


def var(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_") or "x"


def limpar(t: str) -> str:
    t = RE_URL.sub(" ", t).replace("*", " ")
    t = re.sub(r"(?<!\w)#(\w+)", r"hashtag_\1", t)
    t = re.sub(r"(?<![\w.])@(\w+)", r"arroba_\1", t)
    return " ".join(t.split())


def main(argv=None, root=None) -> int:
    root = Path(root or ".")
    saida = root / "data/corpus"
    man = {"gerado_em_utc": now_utc(), "formato": "IRaMuTeQ (**** *variáveis)", "idioma_dos_textos": "espanhol (como publicado)",
           "variaveis": ["ator", "rede", "mes", "tipo"], "redes": {}}
    tudo = []
    for rede in comum.REDES:
        posts = sorted(comum.ler_acervo(root / "data" / rede / "posts.csv.gz").values(), key=lambda r: (r["publicado_em"], r["post_id"]))
        blocos = []
        for r in posts:
            txt = limpar(r["texto"])
            if txt:
                blocos.append(f"**** *ator_{var(r['ator_id'])} *rede_{rede} *mes_{r['publicado_em'][:4]}_{r['publicado_em'][5:7]} *tipo_{var(r['tipo'])}\n{txt}\n")
        man["redes"][rede] = {"posts_no_acervo": len(posts), "textos_no_corpus": len(blocos), "sem_texto": len(posts) - len(blocos)}
        if blocos:
            saida.mkdir(parents=True, exist_ok=True)
            (saida / f"{rede}_iramuteq.txt").write_text("\n".join(blocos), encoding="utf-8")
        tudo += blocos
    if not tudo:
        print("corpus: ⛔ acervo vazio, nada exportado")
        return 0
    (saida / "odi_espanha_iramuteq.txt").write_text("\n".join(tudo), encoding="utf-8")
    man["textos_no_corpus"] = len(tudo)
    (saida / "manifesto.json").write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"corpus: {len(tudo)} textos · " + " · ".join(f"{r} {v['textos_no_corpus']}" for r, v in man["redes"].items()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
