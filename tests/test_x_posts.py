import csv, datetime as dt, gzip, json, os, shutil, tempfile, unittest
from pathlib import Path

from base import manifesto, projeto, tweet
import collect_x_posts as cx
import comum

HOJE = dt.date(2026, 11, 14)
OK_RUN = {"id": "r1", "status": "SUCCEEDED", "chargedEventCounts": {}}


def acervo(t):
    return list(csv.DictReader(gzip.open(t / "data/x/posts.csv.gz", "rt", encoding="utf-8"), delimiter=";"))


class TestX(unittest.TestCase):
    def test_sem_autorizacao_nao_chama_a_apify(self):
        t, chamadas = projeto(), []
        rc = cx.main(["--carga"], executar=lambda p, c: chamadas.append(p) or (OK_RUN, []), root=t, hoje=HOJE)
        self.assertEqual((rc, chamadas), (1, []))
        self.assertIn("sem autorização de gasto", manifesto(t, "x")["status"])

    def test_teste_filtra_autor_repost_e_periodo(self):
        t, pedidos = projeto({"x": {"teste": {"teto_usd": 0.05}}}), []

        def fake(payload, cap):
            pedidos.append((payload, cap))
            h = payload["searchTerms"][0].split()[0][5:]
            return OK_RUN, [tweet(f"{h}1", h, texto="Hola  #España @Santi_ABASCAL"), tweet(f"{h}2", "outro"), tweet(f"{h}3", h, quando="Mon Feb 09 12:00:00 +0000 2026"),
                            tweet(f"{h}4", h, texto="RT @alguien: cosa", isRetweet=True), tweet(f"{h}5", h, isReply=True), {"noResults": True}]
        self.assertEqual(cx.main(["--teste"], executar=fake, root=t, hoje=HOJE), 0)
        self.assertEqual(pedidos[0][0], {"searchTerms": ["from:vox_es since:2026-02-16 -filter:retweets"], "maxItems": 20, "queryType": "Latest"})
        self.assertEqual({p[0]["searchTerms"][0].split()[0] for p in pedidos}, {"from:vox_es", "from:Santi_ABASCAL", "from:jm_frias"})  # só os confirmados
        rows = {r["post_id"]: r for r in acervo(t)}
        self.assertEqual(sorted(rows), ["Santi_ABASCAL1", "Santi_ABASCAL5", "jm_frias1", "jm_frias5", "vox_es1", "vox_es5"])  # outro autor, antigo e repost ficam fora
        r = rows["vox_es1"]
        self.assertEqual((r["ator_id"], r["rede"], r["texto"], r["publicado_em"], r["tipo"], r["compartilhamentos"]), ("vox", "x", "Hola #España @Santi_ABASCAL", "2026-09-02T12:00:00Z", "post", "4"))
        self.assertEqual(rows["vox_es5"]["tipo"], "resposta")
        m = manifesto(t, "x")
        self.assertEqual(m["status"], "ok")
        self.assertEqual(m["perfis"][0]["universo"]["posts_total_plataforma"], 90000)
        self.assertIsNone(m["perfis"][0]["universo"]["posts_no_periodo_plataforma"])  # o X não informa: nunca estimado
        self.assertEqual(m["perfis"][0]["cobertura"], "teste (não mede cobertura)")
        self.assertEqual(sorted(p["ator_id"] for p in m["perfis_fora_da_coleta"]), ["cader", "disenso", "foro-madrid"])
        self.assertIn("vox;Vox;x;vox_es;https://x.com/vox_es;VOX;600000;90000", (t / "data/perfis/x_latest.csv").read_text(encoding="utf-8"))

    def test_carga_cobertura_completa_ou_parcial(self):
        t = projeto({"x": {"carga": {"teto_usd": 1.0, "posts_por_perfil": {"padrao": 3, "vox_es": 2}}}})

        def fake(payload, cap):
            h = payload["searchTerms"][0].split()[0][5:]
            return OK_RUN, [tweet(f"{h}{i}", h) for i in range(2)]
        self.assertEqual(cx.main(["--carga"], executar=fake, root=t, hoje=HOJE), 0)
        m = manifesto(t, "x")
        cob = {p["perfil"]: p["cobertura"] for p in m["perfis"]}
        self.assertTrue(cob["vox_es"].startswith("parcial ⛔"))      # vieram 2 de 2 pedidos: parou no limite
        self.assertTrue(cob["jm_frias"].startswith("completa"))      # vieram 2 de 3: parou pela data
        self.assertTrue(m["status"].startswith("parcial"))

    def test_teto_corta_os_perfis_seguintes(self):
        t, caps = projeto({"x": {"carga": {"teto_usd": 0.016, "posts_por_perfil": {"padrao": 100}}}}), []

        def fake(payload, cap):
            caps.append(cap)
            return OK_RUN, [tweet(f"{len(caps)}-{i}", payload["searchTerms"][0].split()[0][5:]) for i in range(payload["maxItems"])]
        cx.main(["--carga"], executar=fake, root=t, hoje=HOJE)
        m = manifesto(t, "x")
        self.assertLessEqual(m["custo_usd"], 0.016)
        self.assertTrue(all(c <= 0.016 for c in caps))
        self.assertLess(m["perfis"][1]["pedido"], 100)  # o 2º perfil só recebe o que sobrou
        self.assertIn("teto", m["perfis"][2]["erro"])
        self.assertEqual(m["perfis"][2]["cobertura"], "⛔ não lido")

    def test_erro_em_todos_os_perfis_nao_e_ok(self):
        t = projeto({"x": {"diario": {"teto_dia_usd": 0.1, "teto_mes_usd": 1.0}}})

        def fake(payload, cap):
            raise OSError("HTTP 401")
        self.assertEqual(cx.main(["--diario"], executar=fake, root=t, hoje=HOJE), 1)
        self.assertTrue(manifesto(t, "x")["status"].startswith("⛔ nenhum perfil lido"))

    def test_diario_janela_e_fim_do_periodo(self):
        t, pedidos = projeto({"x": {"diario": {"teto_dia_usd": 0.1, "teto_mes_usd": 1.0}}}), []
        fake = lambda p, c: pedidos.append(p) or (OK_RUN, [{"noResults": True}])  # noqa: E731
        self.assertEqual(cx.main(["--diario"], executar=fake, root=t, hoje=HOJE), 0)
        self.assertIn("since:2026-11-12", pedidos[0]["searchTerms"][0])       # hoje − janela_dias (2)
        self.assertEqual(manifesto(t, "x")["status"], "ok")                    # ninguém postou não é erro
        t2, chamadas = projeto({"x": {"diario": {"teto_dia_usd": 0.1, "teto_mes_usd": 1.0}}}, ate="2026-10-30"), []
        self.assertEqual(cx.main(["--diario"], executar=lambda p, c: chamadas.append(p) or (OK_RUN, []), root=t2, hoje=HOJE), 0)
        self.assertEqual(chamadas, [])                                         # período encerrado: sem custo
        self.assertFalse((t2 / "data/x/manifesto_latest.json").exists())

    def test_data_final_corta_e_entra_na_busca(self):
        t, pedidos = projeto({"x": {"carga": {"teto_usd": 1.0}}}, ate="2026-08-31"), []

        def fake(payload, cap):
            pedidos.append(payload)
            h = payload["searchTerms"][0].split()[0][5:]
            return OK_RUN, [tweet(f"{h}a", h, quando="Mon Aug 31 23:59:00 +0000 2026"), tweet(f"{h}b", h, quando="Tue Sep 01 00:01:00 +0000 2026")]
        cx.main(["--carga"], executar=fake, root=t, hoje=HOJE)
        self.assertIn("until:2026-09-01", pedidos[0]["searchTerms"][0])
        self.assertEqual({r["post_id"][-1] for r in acervo(t)}, {"a"})

    def test_segunda_leitura_atualiza_sem_duplicar(self):
        t = projeto({"x": {"carga": {"teto_usd": 1.0}}})
        cx.main(["--carga"], executar=lambda p, c: (OK_RUN, [tweet("1", "vox_es")] if "vox_es" in p["searchTerms"][0] else []), root=t, hoje=HOJE)
        antes = acervo(t)[0]
        novo = tweet("1", "vox_es")
        novo["likeCount"] = 99
        cx.main(["--carga"], executar=lambda p, c: (OK_RUN, [novo] if "vox_es" in p["searchTerms"][0] else []), root=t, hoje=HOJE)
        depois = acervo(t)
        self.assertEqual(len(depois), 1)
        self.assertEqual((depois[0]["curtidas"], depois[0]["primeira_coleta"]), ("99", antes["primeira_coleta"]))
        self.assertEqual(manifesto(t, "x")["posts_novos"], 0)

    def test_bruto_so_no_privado(self):
        t, priv = projeto({"x": {"teste": {"teto_usd": 0.05}}}), Path(tempfile.mkdtemp())
        os.environ["ATLAS_INTERNO_DIR"] = str(priv)
        try:
            cx.main(["--teste"], executar=lambda p, c: (OK_RUN, [tweet("1", p["searchTerms"][0].split()[0][5:])]), root=t, hoje=HOJE)
        finally:
            del os.environ["ATLAS_INTERNO_DIR"]
        self.assertEqual(len(list((priv / "x").glob("apify_*.jsonl.gz"))), 1)
        self.assertEqual(sorted(p.name for p in (t / "data/x").iterdir() if not p.name.startswith("manifesto")), ["posts.csv.gz"])
        self.assertTrue(manifesto(t, "x")["bruto_no_privado"])
        shutil.rmtree(priv)


class TestComum(unittest.TestCase):
    def test_datas_e_numeros(self):
        self.assertEqual(comum.quando("Wed Oct 15 12:00:00 +0000 2026"), "2026-10-15T12:00:00Z")
        self.assertEqual(comum.quando(1771200000), "2026-02-16T00:00:00Z")
        self.assertEqual(comum.quando("1771200000000"), "2026-02-16T00:00:00Z")
        self.assertEqual(comum.quando("2026-03-01T10:00:00+01:00"), "2026-03-01T09:00:00Z")
        self.assertEqual((comum.inteiro(None), comum.inteiro(""), comum.inteiro("1,234"), comum.inteiro(0)), ("", "", 1234, 0))  # ausente não vira zero


if __name__ == "__main__":
    unittest.main()
