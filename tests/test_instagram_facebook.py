import csv, datetime as dt, gzip, unittest

from base import manifesto, projeto
import collect_facebook_posts as cf
import collect_instagram_posts as ci

HOJE = dt.date(2026, 11, 14)
RUN = {"id": "r", "status": "SUCCEEDED", "chargedEventCounts": {}}


def acervo(t, rede):
    return {r["post_id"]: r for r in csv.DictReader(gzip.open(t / f"data/{rede}/posts.csv.gz", "rt", encoding="utf-8"), delimiter=";")}


class TestInstagram(unittest.TestCase):
    def test_posts_e_visualizacoes_dos_reels(self):
        t, pedidos = projeto({"instagram": {"carga": {"teto_usd": 0.5}}}), []

        def fake(payload, cap):
            pedidos.append(payload)
            if payload["resultsType"] == "reels":
                return RUN, [{"shortCode": "AAA", "videoPlayCount": 5000, "videoDuration": 31.4}]
            return RUN, [{"shortCode": "AAA", "timestamp": "2026-03-01T10:00:00.000Z", "caption": "España\nprimero", "likesCount": -1, "commentsCount": 7, "ownerUsername": "vox_es", "displayUrl": "https://img/a.jpg"},
                         {"shortCode": "BBB", "timestamp": "2026-03-02T10:00:00.000Z", "caption": "foto", "likesCount": 12, "commentsCount": 0, "ownerUsername": "vox_es"},
                         {"shortCode": "CCC", "timestamp": "2026-03-03T10:00:00.000Z", "caption": "de outro", "ownerUsername": "outra_conta"},
                         {"shortCode": "DDD", "caption": "sem data", "ownerUsername": "vox_es"}]
        self.assertEqual(ci.main(["--carga"], executar=fake, root=t, hoje=HOJE), 0)
        self.assertEqual([p["resultsType"] for p in pedidos], ["posts", "reels"])  # só o Vox está confirmado no Instagram
        self.assertEqual((pedidos[0]["directUrls"], pedidos[0]["onlyPostsNewerThan"]), (["vox_es"], "2026-02-16"))
        rows = acervo(t, "instagram")
        self.assertEqual(sorted(rows), ["AAA", "BBB"])  # de outro perfil e sem data ficam fora
        a = rows["AAA"]
        self.assertEqual((a["tipo"], a["visualizacoes"], a["duracao_s"], a["curtidas"], a["comentarios"], a["texto"]), ("vídeo", "5000", "31", "", "7", "España primero"))  # -1 = curtidas ocultas, não vira número
        self.assertEqual((rows["BBB"]["tipo"], rows["BBB"]["visualizacoes"], rows["BBB"]["curtidas"]), ("post", "", "12"))
        p = manifesto(t, "instagram")["perfis"][0]
        self.assertEqual((p["lidos_no_periodo"], p["sem_data"], p["complemento_itens"]), (2, 1, 1))
        self.assertTrue(p["cobertura"].startswith("completa"))


class TestFacebook(unittest.TestCase):
    def test_limite_do_ator_marca_parcial(self):
        t = projeto({"facebook": {"carga": {"teto_usd": 9.0}}})

        def fake(payload, cap):
            return RUN, [{"postId": str(i), "url": f"https://www.facebook.com/vox.espana/posts/{i}", "time": "2026-05-01T08:00:00.000Z", "text": f"post {i}",
                          "likes": 5, "comments": 1, "shares": 2, **({"viewsCount": 100, "isVideo": True} if i == 0 else {})} for i in range(700)]
        self.assertEqual(cf.main(["--carga"], executar=fake, root=t, hoje=HOJE), 0)
        m = manifesto(t, "facebook")
        p = m["perfis"][0]
        self.assertEqual(p["pedido"], 1714)                           # o teto reduziu o pedido de 3.000 ((9,00 − 0,001) ÷ 0,005 ÷ 1,05)
        self.assertTrue(p["bateu_no_limite_do_ator"])
        self.assertEqual(p["cobertura"], "parcial ⛔: a leitura parou no limite do ator, não pela data")
        self.assertEqual(m["custo_usd"], 3.501)                       # 700 × 0,005 + 0,001 de início
        rows = acervo(t, "facebook")
        self.assertEqual((len(rows), rows["0"]["tipo"], rows["0"]["visualizacoes"], rows["1"]["tipo"], rows["1"]["curtidas"], rows["1"]["compartilhamentos"]), (700, "vídeo", "100", "post", "5", "2"))


if __name__ == "__main__":
    unittest.main()
