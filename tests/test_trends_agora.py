import json, shutil, unittest

from base import RAIZ, projeto
import collect_trends_agora as ca

ALTA = '''<rss xmlns:ht="https://trends.google.com/trending/rss"><channel>
<item><title>abascal</title><ht:approx_traffic>2000+</ht:approx_traffic><pubDate>Sun, 15 Nov 2026 10:00:00 -0800</pubDate>
<ht:news_item><ht:news_item_title>Abascal en Madrid</ht:news_item_title><ht:news_item_url>https://ex.es/a</ht:news_item_url><ht:news_item_source>Ex</ht:news_item_source></ht:news_item></item>
<item><title>real madrid</title><ht:approx_traffic>50000+</ht:approx_traffic><pubDate>Sun, 15 Nov 2026 09:00:00 -0800</pubDate></item></channel></rss>'''
NOT = '<rss><channel>' + "".join(f'<item><title>Titular {i} - Diario</title><link>https://ex.es/{i}</link><pubDate>Sun, 15 Nov 2026 1{i}:00:00 GMT</pubDate><source url="https://ex.es">Diario</source></item>' for i in range(7)) + '</channel></rss>'


class TestTrendsAgora(unittest.TestCase):
    def test_parse(self):
        a = ca.parse_alta(ALTA)
        self.assertEqual([(x["pos"], x["termo"], x["trafego_aproximado"], x["cita_ator"]) for x in a], [(1, "abascal", "2000+", True), (2, "real madrid", "50000+", False)])
        self.assertEqual((a[0]["publicado_em"], a[0]["noticias"][0]["fonte"]), ("2026-11-15T18:00:00Z", "Ex"))
        n = ca.parse_noticias(NOT)
        self.assertEqual((len(n), n[0]["titulo"], n[0]["fonte"], n[4]["pos"]), (5, "Titular 0", "Diario", 5))

    def test_grava_e_nao_duplica_o_dia(self):
        t = projeto()
        shutil.copy(RAIZ / "data/config/trends.json", t / "data/config/trends.json")
        buscar = lambda u: ALTA if "trending" in u else NOT  # noqa: E731
        self.assertEqual(ca.main(root=t, buscar=buscar), 0)
        self.assertEqual(ca.main(root=t, buscar=buscar), 0)
        termos = json.loads((t / "data/config/trends.json").read_text(encoding="utf-8"))["noticias_termos"]
        linhas = (t / "data/trends/noticias_historico.csv").read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(linhas) - 1, 5 * len(termos))                       # a 2ª leitura do mesmo dia não duplica
        self.assertEqual(len(json.loads((t / "data/trends/agora.json").read_text(encoding="utf-8"))["itens"]), 2)

    def test_sem_rede_fica_bloqueado(self):
        t = projeto()
        shutil.copy(RAIZ / "data/config/trends.json", t / "data/config/trends.json")

        def cai(u):
            raise OSError
        self.assertEqual(ca.main(root=t, buscar=cai), 1)
        self.assertFalse((t / "data/trends/agora.json").exists())


if __name__ == "__main__":
    unittest.main()
