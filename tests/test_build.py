import datetime as dt, json, unittest

from base import RAIZ, projeto, tweet
import build_acervo, build_rede_mencoes, build_saude_coleta, exportar_corpus, resolver_conflitos
import collect_x_posts as cx

HOJE = dt.date(2026, 11, 14)
RUN = {"id": "r", "status": "SUCCEEDED", "chargedEventCounts": {}}


def com_dados():
    t = projeto({"x": {"carga": {"teto_usd": 1.0}, "diario": {"teto_dia_usd": 0.1, "teto_mes_usd": 1.0}}})

    def fake(payload, cap):
        h = payload["searchTerms"][0].split()[0][5:]
        return RUN, [tweet(f"{h}1", h, texto="Con @Santi_ABASCAL en #Madrid https://t.co/x *ojo*"), tweet(f"{h}2", h, quando="Tue Mar 03 09:00:00 +0000 2026", texto="#Madrid otra vez con @ForoMadrid_")]
    cx.main(["--carga"], executar=fake, root=t, hoje=HOJE)
    return t


class TestBuild(unittest.TestCase):
    def test_sem_coleta_nao_vira_zero(self):
        t = projeto()
        self.assertEqual(build_acervo.main(root=t), 0)
        r = json.loads((t / "data/site/resumo.json").read_text(encoding="utf-8"))
        self.assertIsNone(r["totais"]["posts"])
        self.assertEqual((r["totais"]["perfis_previstos"], r["totais"]["perfis_confirmados"], r["totais"]["perfis_candidatos"], r["totais"]["perfis_nao_localizados"]), (18, 5, 8, 5))
        self.assertTrue(all(p["posts_no_acervo"] is None and p["universo"] is None for p in r["perfis"]))
        self.assertEqual({p["situacao"] for p in r["perfis"]}, {"confirmado", "candidato a conferir", "não localizado"})
        self.assertEqual(json.loads((t / "data/site/indice.json").read_text(encoding="utf-8")), {"meses": []})

    def test_resumo_com_dados(self):
        t = com_dados()
        build_acervo.main(root=t)
        r = json.loads((t / "data/site/resumo.json").read_text(encoding="utf-8"))
        self.assertEqual(r["totais"]["posts"], 6)
        vox = next(p for p in r["perfis"] if p["rede"] == "x" and p["perfil"] == "vox_es")
        self.assertEqual((vox["posts_no_acervo"], vox["universo"]["posts_total_plataforma"], vox["universo_no_periodo"]), (2, 90000, None))
        self.assertTrue(vox["cobertura_do_periodo"].startswith("completa"))
        self.assertIn({"mes": "2026-03", "ator_id": "vox", "rede": "x", "posts": 1}, r["por_mes"])
        self.assertIn({"ator_id": "vox", "tag": "madrid", "posts": 2}, r["hashtags"])
        self.assertIn({"ator_id": "abascal", "rede": "x", "conta": "foromadrid_", "posts": 1}, r["mencoes"])
        self.assertNotIn("santi_abascal", [m["conta"] for m in r["mencoes"] if m["ator_id"] == "abascal"])  # não conta a si mesmo
        idx = json.loads((t / "data/site/indice.json").read_text(encoding="utf-8"))["meses"]
        self.assertEqual([(m["mes"], m["posts"]) for m in idx], [("2026-09", 3), ("2026-03", 3)])
        p = json.loads((t / "data/site/posts-2026-09.json").read_text(encoding="utf-8"))[0]
        self.assertEqual((p["c"], p["m"], p["s"], p["v"]), (10, 2, 4, 1000))

    def test_corpus_iramuteq(self):
        t = com_dados()
        exportar_corpus.main(root=t)
        txt = (t / "data/corpus/odi_espanha_iramuteq.txt").read_text(encoding="utf-8")
        self.assertIn("**** *ator_vox *rede_x *mes_2026_09 *tipo_post\nCon arroba_Santi_ABASCAL en hashtag_Madrid ojo\n", txt)  # sem endereço e sem asterisco
        self.assertEqual(txt.count("****"), 6)
        self.assertEqual(json.loads((t / "data/corpus/manifesto.json").read_text(encoding="utf-8"))["redes"]["x"], {"posts_no_acervo": 6, "textos_no_corpus": 6, "sem_texto": 0})

    def test_rede_de_mencoes(self):
        t = com_dados()
        build_rede_mencoes.main(root=t)
        arestas = (t / "data/redes/mencoes_arestas.csv").read_text(encoding="utf-8")
        self.assertIn("x:vox_es;x:santi_abascal;Directed;1", arestas)
        self.assertNotIn("x:santi_abascal;x:santi_abascal", arestas)
        nos = (t / "data/redes/mencoes_nos.csv").read_text(encoding="utf-8")
        self.assertIn("x:santi_abascal;@santi_abascal;x;monitorado;Santiago Abascal;2", nos)
        self.assertIn("x:foromadrid_;@foromadrid_;x;marcado;;3", nos)       # candidato ainda não confirmado entra só como conta marcada
        self.assertIn('<edge id="0" source="x:jm_frias"', (t / "data/redes/mencoes.gexf").read_text(encoding="utf-8"))

    def test_saude(self):
        t = projeto()
        agora = dt.datetime(2026, 11, 14, 12, tzinfo=dt.timezone.utc)
        self.assertEqual(build_saude_coleta.main(["--falhar"], root=t, agora=agora), 0)   # nada autorizado: inativa não é atraso
        s = json.loads((t / "data/saude_coleta.json").read_text(encoding="utf-8"))
        self.assertTrue(all(x["situacao"].startswith("inativa") for x in s["series"]))
        t = com_dados()
        self.assertEqual(build_saude_coleta.main(["--falhar"], root=t, agora=dt.datetime.now(dt.timezone.utc)), 0)
        s = {x["serie"]: x["situacao"] for x in json.loads((t / "data/saude_coleta.json").read_text(encoding="utf-8"))["series"]}
        self.assertEqual((s["x"], s["instagram"][:7]), ("em dia", "inativa"))
        depois = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=40)
        self.assertEqual(build_saude_coleta.main(["--falhar"], root=t, agora=depois), 1)   # 40 h sem dado novo: atrasada, workflow vermelho
        self.assertTrue(json.loads((t / "data/saude_coleta.json").read_text(encoding="utf-8"))["atrasadas"][0].startswith("Posts · X"))

    def test_resolver_conflitos_junta_perfis(self):
        cab = "ator_id;ator_nome;rede;perfil;url;nome_exibido;seguidores;posts_total;verificado;captured_at;fonte\n"
        base = cab + "vox;Vox;instagram;vox_es;u;V;10;1;;2026-11-13;f\nvox;Vox;facebook;vox.espana;u;V;20;;;2026-11-14;f\n"
        nova = cab + "vox;Vox;instagram;vox_es;u;V;11;1;;2026-11-14;f\n"
        u = resolver_conflitos.unir_csv(base, nova).splitlines()
        self.assertEqual(len(u), 3)
        self.assertIn("vox;Vox;instagram;vox_es;u;V;11;1;;2026-11-14;f", u)   # fica a captura mais recente; a outra rede não se perde


class TestConfig(unittest.TestCase):
    """A configuração publicada precisa respeitar as regras do projeto (AGENTS.md)."""

    def test_perfil_confirmado_tem_fonte(self):
        for a in json.loads((RAIZ / "data/config/atores.json").read_text(encoding="utf-8"))["atores"]:
            self.assertEqual(sorted(a["perfis"]), ["facebook", "instagram", "x"], a["id"])
            for rede, p in a["perfis"].items():
                if p.get("confirmado"):
                    self.assertTrue(p["perfil"] and p["url"].startswith("https://") and len(p.get("fonte", "")) > 20 and p.get("conferido_em"), f"{a['id']}/{rede}: confirmado sem fonte")

    def test_teto_so_com_autorizacao_escrita(self):
        c = json.loads((RAIZ / "data/config/coleta.json").read_text(encoding="utf-8"))
        for nome, bloco in list(c["redes"].items()) + [("perfis", c["perfis"])]:
            tetos = [v for modo in ("teste", "carga", "diario", "sonda") for k, v in (bloco.get(modo) or {}).items() if k.startswith("teto")]
            if any(float(v) > 0 for v in tetos):
                self.assertGreater(len(bloco.get("autorizacao", "")), 20, f"{nome}: teto maior que zero sem a frase de autorização do responsável")

    def test_sem_token_no_repositorio(self):
        import re
        for p in list((RAIZ / "scripts").glob("*")) + list((RAIZ / "data/config").glob("*")) + list((RAIZ / ".github/workflows").glob("*")):
            if p.is_file():
                self.assertIsNone(re.search(r"apify_api_[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{30,}", p.read_text(encoding="utf-8", errors="ignore")), p.name)


if __name__ == "__main__":
    unittest.main()
