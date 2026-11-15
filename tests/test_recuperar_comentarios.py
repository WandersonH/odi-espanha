import csv, gzip, json, os, shutil, tempfile, unittest
from pathlib import Path

from base import RAIZ, projeto
import collect_comentarios_youtube as cy
import collect_google_transparencia as cg
import collect_meta_anuncios_apify as cm
import comum
import recuperar_bruto as rb


def ambiente(**env):
    antigo = {k: os.environ.get(k) for k in ("ATLAS_INTERNO_DIR", "ODI_INTERNO_DIR")}
    for k in antigo:
        os.environ.pop(k, None)
    os.environ.update(env)
    return antigo


def restaurar(antigo):
    for k, v in antigo.items():
        os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)


class TestRecuperarBruto(unittest.TestCase):
    def test_sem_privado_nada_e_baixado(self):
        t, ant = projeto(), ambiente()
        try:
            self.assertEqual(rb.main(root=t, listar=lambda a: self.fail("não deveria listar"), baixar=lambda d: self.fail("não deveria baixar")), 1)
        finally:
            restaurar(ant)
        self.assertTrue(json.loads((t / "data/bruto_privado.json").read_text(encoding="utf-8"))["status"].startswith("⛔"))

    def test_baixa_uma_vez_cada_execucao_e_publica_so_contagens(self):
        t, priv = projeto(), Path(tempfile.mkdtemp())
        ant = ambiente(ATLAS_INTERNO_DIR=str(priv))
        baixados = []

        def baixar(ds):
            baixados.append(ds)
            return [] if ds == "vazio" else [{"texto": "segredo de terceiro", "n": 1}, {"n": 2}]
        listar = lambda a: [{"id": "r1", "defaultDatasetId": "d1", "status": "SUCCEEDED"}, {"id": "r2", "defaultDatasetId": "vazio", "status": "SUCCEEDED"}] if "x-tweet" in a else []  # noqa: E731
        try:
            self.assertEqual(rb.main(root=t, listar=listar, baixar=baixar), 0)
            self.assertEqual(rb.main(root=t, listar=listar, baixar=baixar), 0)   # 2ª vez: nada é baixado de novo
        finally:
            restaurar(ant)
        self.assertEqual(sorted(baixados), ["d1", "vazio"])
        arq = next(priv.glob("apify_execucoes/*/r1.jsonl.gz"))
        self.assertEqual(len(gzip.open(arq, "rt", encoding="utf-8").read().splitlines()), 2)
        pub = (t / "data/bruto_privado.json").read_text(encoding="utf-8")
        self.assertNotIn("segredo de terceiro", pub)
        reg = next(v for k, v in json.loads(pub)["por_ator"].items() if "x-tweet" in k)
        self.assertEqual((reg["execucoes_encontradas"], reg["ja_gravadas"], reg["gravadas_agora"]), (2, 2, 0))


def videos(t, linhas):
    ac = {}
    for vid, ator, n in linhas:
        ac[vid] = {**{c: "" for c in comum.COLS}, "post_id": vid, "ator_id": ator, "ator_nome": ator, "rede": "youtube", "publicado_em": "2026-09-01T10:00:00Z", "comentarios": n}
    comum.gravar_acervo(t / "data/youtube/posts.csv.gz", ac)
    shutil.copy(RAIZ / "data/config/comentarios.json", t / "data/config/comentarios.json")


class TestComentariosYoutube(unittest.TestCase):
    def test_sem_privado_nao_le_nada(self):
        t, ant = projeto(), ambiente()
        videos(t, [("v1", "vox", "3")])
        try:
            self.assertEqual(cy.main(root=t, buscar=lambda *a: self.fail("não deveria chamar a API")), 1)
        finally:
            restaurar(ant)
        self.assertTrue(json.loads((t / "data/youtube/comentarios/cobertura.json").read_text(encoding="utf-8"))["status"].startswith("⛔"))

    def test_le_tudo_guarda_texto_so_no_privado_e_publica_contagens(self):
        t, priv, chamadas = projeto(), Path(tempfile.mkdtemp()), []
        ant = ambiente(ATLAS_INTERNO_DIR=str(priv))
        videos(t, [("v1", "vox", "9"), ("v2", "vox", ""), ("v3", "vox", "0")])
        c = lambda i, txt, pai=None: {"id": i, "snippet": {"textOriginal": txt, "authorDisplayName": "Fulana de Tal", "authorChannelId": {"value": "UC" + i[:1]}, "publishedAt": "2026-09-02T00:00:00Z", **({"parentId": pai} if pai else {})}}  # noqa: E731

        def buscar(recurso, p):
            chamadas.append((recurso, p.get("videoId") or p.get("parentId"), p.get("pageToken")))
            if p.get("videoId") == "v2":
                raise cy.ErroAPI("commentsDisabled")
            if recurso == "commentThreads" and not p.get("pageToken"):
                return {"nextPageToken": "p2", "items": [{"snippet": {"topLevelComment": c("a1", "texto secreto um"), "totalReplyCount": 7}, "replies": {"comments": [c("a1.r1", "r", "a1")]}}]}
            if recurso == "commentThreads":
                return {"items": [{"snippet": {"topLevelComment": c("b1", "texto dois"), "totalReplyCount": 1}, "replies": {"comments": [c("b1.r1", "r", "b1")]}}]}
            return {"items": [c(f"a1.r{i}", "resposta", "a1") for i in range(1, 8)]}
        try:
            self.assertEqual(cy.main(root=t, buscar=buscar), 0)
            n1 = len(chamadas)
            self.assertEqual(cy.main(root=t, buscar=buscar), 0)   # tudo completo e contador igual: nenhuma chamada nova
        finally:
            restaurar(ant)
        self.assertEqual((n1, len(chamadas)), (4, 4))             # v1: 2 páginas + respostas de a1; v2: desativados; v3 (contador 0): nenhuma
        with gzip.open(priv / "youtube/comentarios/comentarios.csv.gz", "rt", encoding="utf-8", newline="") as f:
            linhas = list(csv.DictReader(f, delimiter=";"))
        self.assertEqual((len(linhas), sum(1 for r in linhas if r["resposta_a"] == "a1")), (10, 7))
        pub = (t / "data/youtube/comentarios/cobertura.json").read_text(encoding="utf-8")
        for proibido in ("texto secreto", "Fulana", "UCa"):
            self.assertNotIn(proibido, pub)
        o = json.loads(pub)["atores"]["vox"]
        self.assertEqual((o["universo_comentarios"], o["videos_com_contador"], o["comentarios_lidos"], o["dos_quais_respostas"], o["videos_com_comentarios_desativados"]), (9, 2, 10, 8, 1))
        self.assertTrue(o["cobertura"].startswith("completa"))

    def test_teto_de_chamadas_deixa_video_incompleto_e_cobertura_parcial(self):
        t, priv = projeto(), Path(tempfile.mkdtemp())
        ant = ambiente(ATLAS_INTERNO_DIR=str(priv))
        videos(t, [("v1", "vox", "500")])
        cfg = json.loads((t / "data/config/comentarios.json").read_text(encoding="utf-8"))
        cfg["youtube"].update(chamadas_por_execucao=2, paralelo=1)
        (t / "data/config/comentarios.json").write_text(json.dumps(cfg), encoding="utf-8")
        n = iter(range(10**6))
        sem_fim = lambda r, p: {"nextPageToken": "x", "items": [{"snippet": {"topLevelComment": {"id": f"c{next(n)}", "snippet": {"textOriginal": "t"}}, "totalReplyCount": 0}}]}  # noqa: E731
        try:
            self.assertEqual(cy.main(root=t, buscar=sem_fim), 0)
        finally:
            restaurar(ant)
        d = json.loads((t / "data/youtube/comentarios/cobertura.json").read_text(encoding="utf-8"))
        self.assertEqual((d["chamadas_nesta_execucao"], d["atores"]["vox"]["comentarios_lidos"]), (2, 2))
        self.assertTrue(d["atores"]["vox"]["cobertura"].startswith("parcial ⛔") and d["status"].startswith("⚠️ parcial"))


class TestAnunciosRecuperacao(unittest.TestCase):
    def test_meta_recuperar_nao_soma_custo_ja_registrado_e_marca_frase_exata(self):
        t, aqui = projeto(), os.getcwd()
        for f in ("meta_anuncios.json", "temas.json"):
            shutil.copy(RAIZ / "data/config" / f, t / "data/config" / f)
        (t / "data/meta").mkdir(parents=True)
        (t / "data/meta/manifesto-2026-11-antes.json").write_text(json.dumps({"custo_usd": 0.03, "runs": [{"id": "run-b"}]}), encoding="utf-8")

        def fake(payload, cap):
            ab = "Abascal" in payload["adLibraryUrls"][0]
            return {"id": "run-a" if ab else "run-b", "status": "SUCCEEDED", "usageTotalUsd": 0.01}, [{"ad_archive_id": "9", "page_name": "Página", "categories": ["POLITICAL"], "gated_type": "TAKEN_DOWN", "currency": "NOK" if ab else "EUR", "spend": "NOK4K - NOK4.5K" if ab else "<€100", "reach_estimate": ">1M",
                                                                                      "snapshot": {"caption": "https://www.elmund0.es/videos.html", "body": {"text": "Con Santiago  ABASCAL en Madrid"}, "cards": [{"title": "Foro abierto"}]}}]
        os.chdir(t)
        try:
            self.assertEqual(cm.main(["--recuperar"], executar=fake), 0)
        finally:
            os.chdir(aqui)
        d = json.loads((t / "data/meta/anuncios.json").read_text(encoding="utf-8"))
        self.assertEqual((d["modo"], d["custo_usd"]), ("recuperação", 0.01))                      # só run-a é nova; run-b já estava em manifesto
        self.assertEqual((d["consultas"]["abascal"]["com_frase_exata"], d["consultas"]["foro-madrid"]["com_frase_exata"]), (1, 0))  # 'foro' e 'madrid' soltos não contam
        self.assertNotIn("ABASCAL en Madrid", (t / "data/meta/anuncios_apify.csv").read_text(encoding="utf-8"))
        q = d["consultas"]["abascal"]
        self.assertEqual((q["classificados_politicos"], q["politicos_retirados_pela_meta"], q["destinos_frase_exata"], q["gasto_por_moeda"]), (1, 1, [["elmund0.es", 1]], {"NOK": {"anuncios": 1, "gasto_min": 4000, "gasto_max": 4500}}))
        self.assertEqual(d["consultas"]["vox"]["gasto_por_moeda"], {"EUR": {"anuncios": 1, "gasto_min": 0, "gasto_max": 100}})
        cab = (t / "data/meta/anuncios_apify.csv").read_text(encoding="utf-8").splitlines()[0]
        self.assertIn("publico_estimado_min", cab)
        self.assertNotIn("alcance", cab)                                                             # ">1M" é tamanho do público-alvo, não alcance

    def test_meta_recuperar_le_do_privado_pelo_termo_do_endereco(self):
        priv = Path(tempfile.mkdtemp())
        d = priv / "apify_execucoes/jmlp~meta-ad-library-scraper"
        d.mkdir(parents=True)
        url = cm.url_biblioteca("Fundación Disenso", "ES", "2026-02-16")
        with gzip.open(d / "RUN1.jsonl.gz", "wt", encoding="utf-8") as f:
            f.write(json.dumps({"ad_archive_id": "1", "page_name": "P", "input": {"url": url}, "snapshot": {"body": {"text": "x"}}}) + "\n")
        g = cm.do_privado(str(priv), "jmlp~meta-ad-library-scraper")
        self.assertEqual({k: (v[0]["id"], len(v[1])) for k, v in g.items()}, {"fundacion disenso": ("RUN1", 1)})
        self.assertEqual(cm.do_privado("", "jmlp~meta-ad-library-scraper"), {})

    def test_google_ausencia_lida_nao_e_falha(self):
        t = projeto()
        shutil.copy(RAIZ / "data/config/google_transparencia.json", t / "data/config/google_transparencia.json")

        def respondeu(cfg):
            cfg["_diag"] = {"rpc_busca": 9, "rpc_anuncios": 3, "buscas": {"VOX": {"sugestoes": 4, "da_regiao": 1, "aceitas": 0}}, "nomes_da_regiao": ["Fulano Vox"]}
            return {}, [], []
        self.assertEqual(cg.main([str(t)], coletar_fn=respondeu), 0)
        d = json.loads((t / "data/google_ads/transparencia.json").read_text(encoding="utf-8"))
        self.assertTrue(d["status"].startswith("ok: a Central respondeu"))
        self.assertNotIn("Fulano", json.dumps(d, ensure_ascii=False))                              # nome sugerido não vai ao público
        self.assertEqual(cg.main([str(t)], coletar_fn=lambda cfg: ({}, [], [])), 1)                 # sem resposta da Central: continua ⛔
        self.assertTrue(json.loads((t / "data/google_ads/transparencia.json").read_text(encoding="utf-8"))["status"].startswith("⛔"))


if __name__ == "__main__":
    unittest.main()


class TestGuardadaNoPrivado(unittest.TestCase):
    def test_acha_a_execucao_do_perfil_que_ainda_nao_esta_em_manifesto(self):
        priv = Path(tempfile.mkdtemp())
        d = priv / "apify_execucoes/apify~facebook-posts-scraper"
        d.mkdir(parents=True)
        for rid, pagina in (("VELHA", "vox.espana"), ("NOVA", "fundaciondisenso"), ("OUTRA", "foromadridoficial")):
            with gzip.open(d / f"{rid}.jsonl.gz", "wt", encoding="utf-8") as f:
                f.write(json.dumps({"facebookUrl": f"https://www.facebook.com/{pagina}", "text": "t"}) + "\n")
        ant = ambiente(ATLAS_INTERNO_DIR=str(priv))
        try:
            achada = comum.guardada_no_privado("apify~facebook-posts-scraper", "FundacionDisenso", {"VELHA"})
            self.assertEqual((achada[0]["id"], len(achada[1])), ("NOVA", 1))
            self.assertIsNone(comum.guardada_no_privado("apify~facebook-posts-scraper", "FundacionDisenso", {"VELHA", "NOVA"}))   # já registrada: não é reaproveitada duas vezes
            self.assertIsNone(comum.guardada_no_privado("apify~facebook-posts-scraper", "perfil_que_nao_existe", set()))
        finally:
            restaurar(ant)
        self.assertIsNone(comum.guardada_no_privado("apify~facebook-posts-scraper", "fundaciondisenso", set()))                # sem privado: nada
