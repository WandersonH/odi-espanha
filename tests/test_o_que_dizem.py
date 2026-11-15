import json, unittest

from base import RAIZ, projeto
import texto as tx


class TestTexto(unittest.TestCase):
    def test_regras_do_dicionario(self):
        cfg = json.loads((RAIZ / "data/config/temas.json").read_text(encoding="utf-8"))
        temas, adv, voto = tx.compilar(cfg)
        c = tx.classificar("¡Prioridad Nacional! La INMIGRACIÓN ilegal y la vivienda. Sánchez traidor. #VotaVOX https://t.co/x", temas, adv, voto)
        self.assertEqual(set(c["temas"]), {"inmigracion_fronteras", "vivienda", "corrupcion_justicia"})   # acento e caixa não importam; prefixo casa "ilegal", "traidor"
        self.assertTrue(c["cita_adversario"] and c["pede_voto"])
        self.assertEqual(tx.classificar("Buenos días a todos", temas, adv, voto), {"temas": ["sem_tema"], "cita_adversario": False, "pede_voto": False, "cita_brasil": False, "brasil_termos": []})
        self.assertFalse(tx.classificar("el pppp y la appa", temas, adv, voto)["cita_adversario"])       # "pp" só como palavra inteira

    def test_nuvem_conta_publicacoes_e_tira_palavras_vazias(self):
        n = dict(tx.nuvem(["la vivienda digna para los españoles", "vivienda digna ya", "vivienda digna y vivienda digna", "otra cosa"], set(), minimo=3))
        self.assertEqual(n, {"vivienda digna": 3})          # 3 publicações (não 4 ocorrências); o par absorve as palavras soltas

    def test_trecho_repetido_no_perfil_sai_do_texto_util(self):
        pubs = [{"perfil": "p", "texto": f"Mensaje número {i} sobre vivienda. Suscríbete a nuestro canal oficial."} for i in range(12)]
        util = tx.texto_util(pubs[0], tx.texto_padrao(pubs))
        self.assertIn("vivienda", util)
        self.assertNotIn("Suscríbete", util)


class TestBuild(unittest.TestCase):
    def test_conteudo_por_ator(self):
        import datetime as dt
        import shutil
        import build_o_que_dizem, collect_x_posts as cx
        from base import tweet
        t = projeto({"x": {"carga": {"teto_usd": 1.0}}})
        shutil.copy(RAIZ / "data/config/temas.json", t / "data/config/temas.json")
        run = {"id": "r", "status": "SUCCEEDED", "chargedEventCounts": {}}
        cx.main(["--carga"], executar=lambda p, c: (run, [tweet("1", "vox_es", texto="La vivienda es prioridad nacional #VotaVOX"), tweet("2", "vox_es", texto="Hola")] if "vox_es" in p["searchTerms"][0] else []), root=t, hoje=dt.date(2026, 11, 14))
        self.assertEqual(build_o_que_dizem.main(root=t), 0)
        c = json.loads((t / "data/x/conteudo.json").read_text(encoding="utf-8"))
        v = c["atores"]["vox"]
        self.assertEqual((v["total_publicacoes"], v["por_tema"], v["pede_voto"]), (2, {"inmigracion_fronteras": 1, "vivienda": 1, "sem_tema": 1}, 1))
        self.assertEqual(c["cobertura_do_dicionario"], {"publicacoes": 2, "com_tema": 1, "sem_tema": 1, "pct_com_tema": 50.0})
        self.assertEqual(v["publicacoes"][0]["taxa_interacao"], 0.016)     # (10 + 2 + 4) ÷ 1000
        self.assertFalse((t / "data/instagram/conteudo.json").exists())    # rede sem acervo: nada gerado, nada inventado


if __name__ == "__main__":
    unittest.main()


class TestCitaBrasil(unittest.TestCase):
    def test_etiqueta_cita_o_brasil(self):
        import json
        from base import RAIZ
        cfg = json.loads((RAIZ / "data/config/temas.json").read_text(encoding="utf-8"))
        temas, adv, voto = tx.compilar(cfg)
        br = tx.compilar_brasil(cfg)
        sim = {"Con @jairbolsonaro y Flávio Bolsonaro en Madrid": ["bolsonaro", "jairbolsonaro"], "Lula da Silva y el Foro de São Paulo": ["lula"],
               "Los brasileños merecen libertad #BrasilLibre": ["brasilenos", "brasillibre"], "#BolsonaroLibre": ["bolsonarolibre"], "Elecciones en Brazil": ["brazil"]}
        for texto, termos in sim.items():
            c = tx.classificar(texto, temas, adv, voto, br)
            self.assertEqual((c["cita_brasil"], c["brasil_termos"]), (True, termos), texto)
        for texto in ("La célula del partido", "Abrasivo y sin lulaby", "Buenos días España"):
            self.assertFalse(tx.classificar(texto, temas, adv, voto, br)["cita_brasil"], texto)
        self.assertFalse(tx.classificar("Lula y Bolsonaro", temas, adv, voto)["cita_brasil"])     # sem os termos, a etiqueta não é aplicada


class TestTrendsConfig(unittest.TestCase):
    def test_config_da_espanha(self):
        import json
        from base import RAIZ
        import collect_trends as ct
        c = json.loads((RAIZ / "data/config/trends.json").read_text(encoding="utf-8"))
        self.assertEqual((c["geo"], ct.GEO, ct.HL), ("ES", "ES", "es"))
        for g in c["grupos"]:
            self.assertLessEqual(len(g["termos"]), 5, g["nome"])                      # o Trends compara no máximo 5 termos
        self.assertTrue(set(c["relacionados"]["grupos"]) <= {g["nome"] for g in c["grupos"]})
        self.assertNotIn("BR", (RAIZ / "scripts/build_trends_caderno.py").read_text(encoding="utf-8").replace("BRT", ""))


class TestRedeCoocorrencia(unittest.TestCase):
    def test_montar_e_deterministico_e_marca_ator_dominante(self):
        import build_rede_coocorrencia as br
        pubs = [("vox", {"espana", "sanchez", "#x"})] * 9 + [("disenso", {"espana", "libertad"})] * 9 + [("disenso", {"libertad", "sanchez"})] * 4
        g1, g2 = br.montar(pubs, ["vox", "disenso"], min_pubs=8, min_peso=3), br.montar(pubs, ["vox", "disenso"], min_pubs=8, min_peso=3)
        self.assertEqual(sorted(g1.edges(data=True)), sorted(g2.edges(data=True)))
        self.assertEqual((g1.nodes["sanchez"]["dominante"], g1.nodes["libertad"]["dominante"], g1.nodes["espana"]["pubs"]), ("vox", "disenso", 18))
        self.assertEqual(g1["espana"]["sanchez"]["weight"], 9)
