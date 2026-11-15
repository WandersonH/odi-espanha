#!/usr/bin/env python3
"""Telegram: mensagens de canais PÚBLICOS dos atores, pela prévia pública na web (https://t.me/s/<canal>). Sem custo, sem login.

Lê só os canais confirmados de data/config/telegram.json. Pagina do mais novo para o mais antigo (?before=<nº>) até passar da
data inicial do período. Universo: o Telegram informa o nº de inscritos; não informa o total de mensagens. O maior número de
mensagem é só um teto (a numeração inclui mensagens apagadas e avisos), e é registrado como tal, nunca como universo.

Saídas públicas (conteúdo publicado pelo próprio canal): data/telegram/posts.csv.gz (mesmas colunas do acervo das outras redes),
data/telegram/resumo.json (universo × lido, por mês, etiqueta 'cita o Brasil', últimas mensagens) e manifesto.
"""
from __future__ import annotations

import html
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comum  # noqa: E402
import texto as tx  # noqa: E402
from net import now_utc, open_url, read_body  # noqa: E402

BLOCO = re.compile(r'data-post="([^"/]+)/(\d+)"')


def numero(s: str):
    m = re.match(r"\s*([\d.,]+)\s*([KkMm]?)", s or "")
    if not m:
        return ""
    return int(round(float(m.group(1).replace(",", ".")) * {"k": 1e3, "m": 1e6, "": 1}[m.group(2).lower()]))


def limpar(h: str) -> str:
    t = re.sub(r"<br\s*/?>", "\n", h)
    return html.unescape(re.sub(r"<[^>]+>", "", t)).strip()


def parse(pagina: str) -> tuple[list[dict], dict]:
    """Mensagens de uma página da prévia e dados do canal (inscritos, nome)."""
    canal = {}
    m = re.search(r'<span class="counter_value">([^<]+)</span>\s*<span class="counter_type">subscribers?</span>', pagina)
    if m:
        canal["inscritos"], canal["inscritos_exibido"] = numero(m.group(1)), m.group(1).strip()
    m = re.search(r'<div class="tgme_channel_info_header_title"[^>]*>\s*<span[^>]*>(.*?)</span>', pagina, re.S)
    if m:
        canal["nome_exibido"] = limpar(m.group(1))
    marcas = list(BLOCO.finditer(pagina))
    msgs = []
    for i, b in enumerate(marcas):
        trecho = pagina[b.start():marcas[i + 1].start() if i + 1 < len(marcas) else len(pagina)]
        d = re.search(r'tgme_widget_message_date"[^>]*>\s*<time datetime="([^"]+)"', trecho)
        if not d:
            continue  # aviso de serviço, sem data: não é publicação
        t = re.search(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', trecho, re.S)
        v = re.search(r'tgme_widget_message_views">([^<]+)<', trecho)
        tipo = "vídeo" if "tgme_widget_message_video" in trecho else "foto" if "tgme_widget_message_photo" in trecho else "texto"
        msgs.append({"canal": b.group(1), "n": int(b.group(2)), "publicado_em": d.group(1)[:19].replace("+00:00", "") + "Z" if d.group(1).endswith("+00:00") else d.group(1),
                     "texto": limpar(t.group(1)) if t else "", "visualizacoes": numero(v.group(1)) if v else "", "tipo": tipo})
    return msgs, canal


def baixar(url: str) -> str:
    with open_url(url, timeout=60, headers={"User-Agent": "Mozilla/5.0 (compatible; ODI-Espanha/1.0; pesquisa acadêmica)", "Accept-Language": "es-ES,es;q=0.9"}) as r:
        return read_body(r).decode("utf-8", "replace")


def main(argv=None, buscar=None, root=None) -> int:
    root = Path(root or ".")
    cfg = json.loads((root / "data/config/telegram.json").read_text(encoding="utf-8"))
    desde, ate = comum.periodo(root)
    pasta, agora = root / "data/telegram", now_utc()
    buscar = buscar or baixar
    acervo = comum.ler_acervo(pasta / "posts.csv.gz")
    brasil = tx.compilar_brasil(json.loads((root / "data/config/temas.json").read_text(encoding="utf-8")))
    man = {"run_started_utc": agora, "rede": "telegram", "ferramenta": "prévia pública t.me/s (sem login)", "modo": "carga", "custo_usd": 0.0, "periodo": {"desde": desde, "ate": ate}, "perfis": []}
    res = {"schema_version": 1, "gerado_em_utc": agora, "fonte": "Telegram · prévia pública na web (t.me/s)", "nota": cfg["nota"], "desde": desde, "canais": []}
    conf = [c for c in cfg["canais"] if c.get("confirmado")]
    erros = 0
    for c in conf:
        info, lidas, paginas, antes, erro, maior, parou_pela_data = {}, 0, 0, None, None, 0, False
        try:
            while paginas < int(cfg.get("max_paginas") or 400):
                msgs, canal = parse(buscar(f"https://t.me/s/{c['canal']}" + (f"?before={antes}" if antes else "")))
                info, paginas = info or canal, paginas + 1
                if not msgs:
                    parou_pela_data = paginas > 1  # acabou o canal: não há nada mais antigo
                    break
                maior = max(maior, max(m["n"] for m in msgs))
                for m in msgs:
                    dia = m["publicado_em"][:10]
                    if dia < desde or (ate and dia > ate):
                        continue
                    pid = f"{m['canal']}/{m['n']}"
                    old = acervo.get(pid) or {}
                    acervo[pid] = {**{k: "" for k in comum.COLS}, "ator_id": c["ator_id"], "ator_nome": c["ator_nome"], "rede": "telegram", "perfil": c["canal"], "post_id": pid,
                                   "url": f"https://t.me/{pid}", "publicado_em": m["publicado_em"], "texto": m["texto"], "tipo": m["tipo"], "visualizacoes": m["visualizacoes"],
                                   "primeira_coleta": old.get("primeira_coleta") or agora, "ultima_coleta": agora}
                    lidas += 1
                if min(m["publicado_em"][:10] for m in msgs) < desde:
                    parou_pela_data = True
                    break
                antes = min(m["n"] for m in msgs)
                if antes <= 1:
                    parou_pela_data = True
                    break
                time.sleep(float(cfg.get("intervalo_s") or 1))
        except Exception as e:  # noqa: BLE001
            erro, erros = type(e).__name__, erros + 1
        meus = [r for r in acervo.values() if r["perfil"] == c["canal"]]
        cob = ("⛔ não lido" if erro and not lidas else "completa: a leitura chegou à data inicial do período" if parou_pela_data and not erro
               else "parcial ⛔: a leitura parou antes da data inicial" + (f" ({erro})" if erro else " (limite de páginas)"))
        br = [r for r in meus if tx.classificar(r["texto"], {}, [], [], brasil)["cita_brasil"]]
        reg = {"ator_id": c["ator_id"], "ator_nome": c["ator_nome"], "canal": c["canal"], "url": c["url"], "nome_exibido": info.get("nome_exibido"),
               "inscritos": info.get("inscritos") if info.get("inscritos") != "" else None, "inscritos_exibido": info.get("inscritos_exibido"),
               "universo_mensagens": None, "universo_nota": "⛔ o Telegram não informa o total de mensagens do canal", "maior_numero_de_mensagem": maior or None,
               "lidas_nesta_execucao": lidas, "no_acervo": len(meus), "paginas_lidas": paginas, "cobertura": cob, "erro": erro,
               "mais_antiga": min((r["publicado_em"] for r in meus), default=None), "mais_recente": max((r["publicado_em"] for r in meus), default=None),
               "por_mes": dict(sorted(Counter(r["publicado_em"][:7] for r in meus).items())), "por_tipo": dict(Counter(r["tipo"] for r in meus).most_common()),
               "sem_texto": sum(1 for r in meus if not r["texto"]), "citam_o_brasil": len(br),
               "ultimas": [{"url": r["url"], "publicado_em": r["publicado_em"], "texto": r["texto"][:300], "visualizacoes": r["visualizacoes"], "tipo": r["tipo"]}
                           for r in sorted(meus, key=lambda r: r["publicado_em"], reverse=True)[:25]]}
        res["canais"].append(reg)
        man["perfis"].append({k: reg[k] for k in ("ator_id", "canal", "lidas_nesta_execucao", "no_acervo", "paginas_lidas", "cobertura", "erro", "mais_antiga", "mais_recente")})
        print(f"{c['ator_nome']} · {c['canal']}: inscritos {reg['inscritos_exibido'] or '⛔'} · lidas no período {len(meus)} ({paginas} páginas) · {cob}")
    res["canais_fora"] = [{"ator_id": c["ator_id"], "canal": c.get("canal"), "motivo": "candidato a conferir"} for c in cfg["canais"] if not c.get("confirmado")]
    if conf:
        comum.gravar_acervo(pasta / "posts.csv.gz", acervo)
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "resumo.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    man["status"] = "⛔ nenhum canal confirmado" if not conf else ("ok" if not erros else f"⚠️ parcial: {erros} canal(is) com erro")
    comum.gravar_manifesto(pasta, man)
    print(f"telegram: {man['status']} · {len(acervo)} mensagens no acervo")
    return 0 if conf and len(acervo) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
