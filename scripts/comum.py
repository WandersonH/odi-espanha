#!/usr/bin/env python3
"""Núcleo dos coletores de posts (Instagram, X, Facebook), portado do padrão do ODI Atlas.

O que cada coletor herda daqui:
- só perfil confirmado em data/config/atores.json é lido; os demais ficam listados no manifesto como fora da coleta;
- teto de gasto: nada roda sem teto autorizado em data/config/coleta.json; cada execução na Apify recebe como teto o que
  sobra do autorizado (uma leitura por vez, pelo custo real da anterior) e não há consulta de saldo da conta;
- período: só entra no acervo o post publicado entre `desde` e `ate` (data UTC) de data/config/projeto.json;
- universo e amostra: para cada perfil o manifesto guarda quanto foi pedido, quanto veio, quanto caiu no período, o post
  mais antigo lido e se a leitura parou pela data (completa) ou pelo limite (parcial ⛔);
- acervo público em data/<rede>/posts.csv.gz (uma linha por post, mesma tabela nas três redes); bruto da Apify só no
  repositório privado (ATLAS_INTERNO_DIR), porque pode trazer dados de terceiros (comentários, marcações).

Modos: --teste (poucos posts por perfil, para conferir ator, preço e perfil), --carga (todo o período) e
--diario (posts dos últimos dias; para sozinho depois da data final do período).
"""
from __future__ import annotations

import csv
import datetime as dt
import gzip
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from apify import custo_run, erro_curto, execucao_anterior, run_actor  # noqa: E402
from net import now_utc  # noqa: E402

REDES_APIFY = ("instagram", "x", "facebook")   # coletores pagos, com teto (comum.rodar)
REDES = REDES_APIFY + ("youtube",)           # todas as redes do acervo (o YouTube usa a API oficial, sem custo)
ROTULO = {"instagram": "Instagram", "x": "X", "facebook": "Facebook", "youtube": "YouTube"}
MODOS = ("teste", "carga", "diario")
COLS = ["ator_id", "ator_nome", "rede", "perfil", "post_id", "url", "publicado_em", "texto", "tipo", "duracao_s",
        "visualizacoes", "curtidas", "comentarios", "compartilhamentos", "primeira_coleta", "ultima_coleta", "capa_url"]
PCOLS = ["ator_id", "ator_nome", "rede", "perfil", "url", "nome_exibido", "seguidores", "posts_total", "verificado", "captured_at", "fonte"]
UTC = dt.timezone.utc


def g(x, *ks):
    """Primeiro campo presente (aceita caminho com ponto)."""
    for k in ks:
        v = x
        for p in k.split("."):
            v = v.get(p) if isinstance(v, dict) else None
        if v not in (None, ""):
            return v
    return None


def inteiro(v):
    """Número inteiro ou "" (ausente nunca vira zero)."""
    if v in (None, "") or isinstance(v, bool):
        return ""
    try:
        return int(float(str(v).replace(",", "")))
    except (TypeError, ValueError):
        return ""


def quando(v) -> str:
    """Data da plataforma (epoch em s ou ms, ISO com ou sem fuso, formato do X) → ISO em UTC. Ilegível volta como veio."""
    if v in (None, ""):
        return ""
    s = str(v).strip()
    try:
        f = float(s)
        return dt.datetime.fromtimestamp(f / 1000 if f > 1e12 else f, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        pass
    for fmt in ("%a %b %d %H:%M:%S %z %Y",):  # 'Wed Oct 15 12:00:00 +0000 2026' (X)
        try:
            return dt.datetime.strptime(s, fmt).astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            pass
    try:
        d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        return (d if d.tzinfo else d.replace(tzinfo=UTC)).astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return s


def hoje_brt() -> dt.date:
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).date()


def ler_json(p: Path):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def periodo(root: Path) -> tuple[str, str | None]:
    p = ler_json(root / "data/config/projeto.json")["periodo"]
    return p["desde"], (p.get("ate") or None)


def perfis_da_rede(root: Path, rede: str) -> tuple[list[dict], list[dict]]:
    """(perfis confirmados, perfis fora da coleta: candidatos a conferir e não localizados)."""
    conf, fora = [], []
    for a in ler_json(root / "data/config/atores.json")["atores"]:
        pf = (a.get("perfis") or {}).get(rede) or {}
        d = {"ator_id": a["id"], "ator_nome": a["nome"], "rede": rede, "perfil": (pf.get("perfil") or "").strip(),
             "url": (pf.get("url") or "").strip(), "confirmado": bool(pf.get("confirmado")) and bool(pf.get("perfil")),
             "fonte": pf.get("fonte") or "", "nota": pf.get("nota") or ""}
        (conf if d["confirmado"] else fora).append(d)
    return conf, fora


def cota(tab, pf: dict) -> int:
    """Posts pedidos por perfil: número fixo ou tabela {"padrao": N, "<perfil>": N}."""
    if isinstance(tab, dict):
        return int(tab.get(pf["perfil"]) or tab.get("padrao") or 0)
    return int(tab or 0)


def ler_acervo(p: Path) -> dict[str, dict]:
    if not p.exists():
        return {}
    with gzip.open(p, "rt", encoding="utf-8") as f:
        return {r["post_id"]: r for r in csv.DictReader(f, delimiter=";")}


def gravar_acervo(p: Path, acervo: dict[str, dict]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with gzip.GzipFile(p, "wb", mtime=0) as bruto:  # mtime fixo: arquivo igual quando o conteúdo é igual
        linhas = sorted(acervo.values(), key=lambda r: (r["ator_id"], r["publicado_em"], r["post_id"]), reverse=True)
        import io
        s = io.StringIO()
        w = csv.DictWriter(s, COLS, delimiter=";", lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(linhas)
        bruto.write(s.getvalue().encode("utf-8"))


def manifestos(pasta: Path) -> list[dict]:
    out = []
    for f in sorted(pasta.glob("manifesto-*.json")):
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
    return out


def gasto(mans: list[dict], modo: str, mes: str | None = None) -> float:
    return round(sum(float(m.get("custo_usd") or 0) for m in mans
                     if m.get("modo") == modo and (mes is None or (m.get("run_started_utc") or "")[:7] == mes)), 5)


def gravar_bruto(rede: str, itens: list, agora: str) -> bool:
    interno = os.environ.get("ATLAS_INTERNO_DIR") or os.environ.get("ODI_INTERNO_DIR")
    if not (interno and itens):
        return False
    d = Path(interno) / rede
    d.mkdir(parents=True, exist_ok=True)
    with gzip.open(d / f"apify_{agora.replace(':', '').replace('-', '')}.jsonl.gz", "wt", encoding="utf-8") as f:
        for x in itens:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    return True


def gravar_manifesto(pasta: Path, man: dict) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    stamp = man["run_started_utc"].replace(":", "").replace("-", "")
    txt = json.dumps(man, ensure_ascii=False, indent=1)
    for nome in (f"manifesto-{stamp}.json", "manifesto_latest.json"):
        (pasta / nome).write_text(txt, encoding="utf-8")


def rodar(rede: str, ad, argv=None, executar=None, root=None, hoje: dt.date | None = None) -> int:
    """Executa um modo de coleta para `rede`. `ad` é o módulo da rede (pedido, e_post, linha e, se houver,
    complemento/unir, universo e depois). `executar(payload, teto)` é injetado nos testes; em produção chama a Apify."""
    argv = list(argv or [])
    root = Path(root or ".")
    modo = next((m for m in MODOS if f"--{m}" in argv), None)
    if not modo:
        print(f"uso: collect_{rede}_posts.py --teste | --carga | --diario")
        return 2
    hoje = hoje or hoje_brt()
    geral = ler_json(root / "data/config/coleta.json")
    cfg, M = geral["redes"][rede], geral["redes"][rede][modo]
    desde_periodo, ate = periodo(root)
    if modo == "diario" and ate and hoje.isoformat() > ate:
        print(f"{rede}: período encerrado em {ate}; o diário não roda mais (sem custo)")
        return 0
    pasta = root / "data" / rede
    agora = now_utc()
    conf, fora = perfis_da_rede(root, rede)
    mans = manifestos(pasta)
    if modo == "diario":
        ja, teto_cfg = gasto(mans, "diario", agora[:7]), float(M["teto_mes_usd"])
        teto = round(min(float(M["teto_dia_usd"]), teto_cfg - ja), 5)
        desde = max(desde_periodo, (hoje - dt.timedelta(days=int(M.get("janela_dias", 1)))).isoformat())
    else:
        ja, teto_cfg = gasto(mans, modo), float(M["teto_usd"])
        teto, desde = round(teto_cfg - ja, 5), desde_periodo
    man = {"run_started_utc": agora, "rede": rede, "ferramenta": f"Apify · {cfg['ator'].replace('~', '/')}", "modo": modo,
           "conta": geral["segredo"], "periodo": {"desde": desde_periodo, "ate": ate}, "desde_leitura": desde,
           "teto_autorizado_usd": teto_cfg, "gasto_antes_usd": ja, "teto_execucao_usd": max(teto, 0.0), "perfis": [],
           "perfis_fora_da_coleta": [{"ator_id": p["ator_id"], "perfil": p["perfil"],
                                      "motivo": "candidato a conferir" if p["perfil"] else (p["nota"] or "não localizado")} for p in fora]}

    def fim(status: str, code: int) -> int:
        man["status"] = status
        gravar_manifesto(pasta, man)
        print(f"{rede} ({modo}): {status}")
        return code

    if not conf:
        return fim("⛔ nenhum perfil confirmado nesta rede (data/config/atores.json)", 1)
    if teto_cfg <= 0 or (modo == "diario" and float(M["teto_dia_usd"]) <= 0):
        return fim(f"⛔ sem autorização de gasto registrada (data/config/coleta.json → redes.{rede}.{modo})", 1)
    if teto < 0.01:
        return fim(f"⛔ teto autorizado esgotado (gasto US$ {ja} de US$ {teto_cfg})", 1)
    token = "x" if executar else os.environ.get(geral["segredo"], "").strip()
    if not token:
        return fim(f"⛔ {geral['segredo']} ausente (cadastre o segredo no GitHub)", 1)
    so_perfis = next((a.split("=", 1)[1].lower().split(",") for a in argv if a.startswith("--perfis=")), None)
    if so_perfis:  # releitura dirigida: só estes perfis (os demais não são tocados)
        conf = [p for p in conf if p["perfil"].lower() in so_perfis]
        man["so_perfis"] = so_perfis
    if not executar and "--recuperar" in argv:
        # Reaproveita execução JÁ PAGA das últimas 48 h cujo resultado não foi baixado; só roda de novo o que não existir.
        corte = (dt.datetime.now(UTC) - dt.timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%S")
        man["recuperacao"] = []

        def executar(pl, cap):
            ant = execucao_anterior(token, cfg["ator"], pl, corte)
            man["recuperacao"].append({"pedido": {k: v for k, v in pl.items() if k not in ("selectedFields",)}, "reaproveitou_execucao": (ant[0] or {}).get("id") if ant else None})
            return ant or run_actor(token, cfg["ator"], pl, cap)
    executar = executar or (lambda pl, cap: run_actor(token, cfg["ator"], pl, cap))

    item, inicio = float(cfg["preco_usd"]["item"]), float(cfg["preco_usd"].get("inicio") or 0)
    lim_ator = int(cfg.get("limite_ator_itens") or 0)
    acervo = ler_acervo(pasta / "posts.csv.gz")
    sobra, brutos, novos_total, mudou = teto, [], 0, False
    for pf in conf:
        n_cfg = int(M["posts"]) if modo == "teste" else cota(M["posts_por_perfil"], pf)
        n = min(n_cfg, int((sobra - inicio) / (item * 1.05))) if item > 0 else n_cfg
        reg = {"ator_id": pf["ator_id"], "ator_nome": pf["ator_nome"], "perfil": pf["perfil"], "pedido": max(n, 0)}
        man["perfis"].append(reg)
        if n < 1:
            reg.update(itens=0, lidos_no_periodo=0, novos=0, cobertura="⛔ não lido", custo_usd=0.0,
                       erro=f"teto de US$ {round(teto, 4)} atingido antes deste perfil (não executado)")
            continue
        cap = round(min(sobra, inicio + item * n * 1.05 + 0.002), 4)
        run, itens, erro = {}, [], None
        try:
            run, itens = executar(ad.pedido(cfg, pf, n, desde, ate, hoje), cap)
            run, itens = run or {}, itens or []
        except Exception as e:  # noqa: BLE001 — o token vai no cabeçalho, nunca na mensagem
            erro = erro_curto(e) if not getattr(e, "run", None) else str(e)
            run = getattr(e, "run", None) or {}  # a execução aconteceu: o custo dela entra no manifesto mesmo sem os itens
        custo = min(cap, max(custo_run(run), round(inicio + item * len(itens), 5))) if run else 0.0
        sobra = round(sobra - custo, 5)
        extra = ad.complemento(cfg, pf, n, desde) if itens and hasattr(ad, "complemento") else None
        if extra:  # 2ª leitura (ex.: visualizações dos reels), com o que sobrou do teto
            if sobra >= 0.01:
                try:
                    cap2 = round(min(sobra, inicio + item * n * 1.05 + 0.002), 4)
                    run2, vistos = executar(extra, cap2)
                    vistos = vistos or []
                    ad.unir(itens, vistos)
                    c2 = min(cap2, max(custo_run(run2 or {}), round(inicio + item * len(vistos), 5)))
                    custo, sobra = custo + c2, round(sobra - c2, 5)
                    reg["complemento_itens"] = len(vistos)
                except Exception as e:  # noqa: BLE001
                    reg["complemento_erro"] = erro_curto(e)
            else:
                reg["complemento_erro"] = "teto atingido antes da 2ª leitura (visualizações ⛔)"
        brutos += itens
        posts = [x for x in itens if ad.e_post(x, pf, cfg)]
        lidos = novos = sem_data = 0
        todas = []
        for x in posts:
            r = ad.linha(x, pf, agora)
            dia = (r["publicado_em"] or "")[:10]
            if len(dia) != 10 or dia[4] != "-":
                sem_data += 1  # sem data não há como dizer se está no período: fica fora e é contado
                continue
            todas.append(r["publicado_em"])
            if not r["post_id"] or dia < desde_periodo or (ate and dia > ate):
                continue
            old = acervo.get(r["post_id"]) or {}
            r["primeira_coleta"] = old.get("primeira_coleta") or agora
            r["capa_url"] = r["capa_url"] or old.get("capa_url", "")
            novos += 0 if old else 1
            acervo[r["post_id"]] = {k: ("" if r.get(k) is None else r.get(k)) for k in COLS}
            lidos, mudou = lidos + 1, True
        no_limite = len(itens) >= n
        no_limite_ator = bool(lim_ator and len(itens) >= lim_ator)
        if erro:
            cobertura = "⛔ não lido"
        elif modo == "teste":
            cobertura = "teste (não mede cobertura)"
        elif no_limite or no_limite_ator:
            cobertura = "parcial ⛔: a leitura parou no limite " + ("do ator" if no_limite_ator and not no_limite else "pedido") + ", não pela data"
        else:
            cobertura = "completa: a leitura parou pela data inicial, não pelo limite"
        reg.update(itens=len(itens), posts_do_perfil=len(posts), itens_de_outra_conta_ou_descartados=len(itens) - len(posts), lidos_no_periodo=lidos, novos=novos, sem_data=sem_data,
                   mais_antigo=min(todas, default=None), mais_recente=max(todas, default=None),
                   bateu_no_limite_pedido=no_limite, bateu_no_limite_do_ator=no_limite_ator, cobertura=cobertura,
                   erro=erro or next((str(x.get("error") or x.get("errorDescription"))[:200] for x in itens if isinstance(x, dict) and x.get("error")), None),
                   run=run.get("id"), custo_usd=round(custo, 5), eventos_cobrados=run.get("chargedEventCounts"))
        if hasattr(ad, "universo"):
            reg["universo"] = ad.universo(itens, pf)
        novos_total += novos
        print(f"{pf['ator_nome']} · {pf['perfil']}: {lidos} posts no período ({len(itens)} itens, pedido {n}) · {cobertura}{' · ' + reg['erro'] if reg['erro'] else ''}")

    if mudou:
        gravar_acervo(pasta / "posts.csv.gz", acervo)
    man["bruto_no_privado"] = gravar_bruto(rede, brutos, agora)
    man.update(custo_usd=round(teto - sobra, 5), posts_novos=novos_total, posts_no_acervo=len(acervo))
    if hasattr(ad, "depois"):
        ad.depois(root, man, conf, agora)
    com_erro = [r for r in man["perfis"] if r.get("erro")]
    parciais = [r for r in man["perfis"] if str(r.get("cobertura", "")).startswith("parcial")]
    print(f"{novos_total} posts novos · acervo {len(acervo)} · {len(com_erro)} perfil(is) com erro · {len(parciais)} no limite")
    if len(com_erro) == len(man["perfis"]):
        return fim(f"⛔ nenhum perfil lido: {com_erro[0]['erro']}", 1)
    if com_erro or parciais:
        return fim(f"parcial: {len(com_erro)} perfil(is) com erro, {len(parciais)} com leitura no limite", 0)
    return fim("ok", 0)
