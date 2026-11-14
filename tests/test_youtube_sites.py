import csv, datetime as dt, gzip, json, os, shutil, tempfile, unittest
from pathlib import Path

from base import manifesto, projeto
import collect_sites as cs
import collect_youtube as cy

HOJE = dt.date(2026, 11, 14)


def com_canal():
    t = projeto()
    p = t / "data/config/atores.json"
    a = json.loads(p.read_text(encoding="utf-8"))
    next(x for x in a["atores"] if x["id"] == "disenso")["perfis"]["youtube"] = {"perfil": "@fundaciondisenso", "url": "https://www.youtube.com/@fundaciondisenso", "confirmado": True, "fonte": "teste"}
    p.write_text(json.dumps(a), encoding="utf-8")
    return t


class TestYouTube(unittest.TestCase):
    def test_formas_de_endereco_e_duracao(self):
        self.assertEqual(cy.alvo({"perfil": "x", "url": "https://www.youtube.com/channel/UCANexQ2_g7B5QgoSIdsHtCQ"}), {"id": "UCANexQ2_g7B5QgoSIdsHtCQ"})
        self.assertEqual(cy.alvo({"perfil": "@fundaciondisenso", "url": "https://www.youtube.com/@fundaciondisenso"}), {"forHandle": "@fundaciondisenso"})
        self.assertEqual(cy.alvo({"perfil": "voxespana", "url": "https://www.youtube.com/user/voxespana"}), {"forUsername": "voxespana"})
        self.assertEqual((cy.duracao("PT1H2M3S"), cy.duracao("PT45S"), cy.duracao(None)), (3723, 45, ""))

    def test_sem_chave_bloqueia(self):
        t = com_canal()
        os.environ.pop("YOUTUBE_API_KEY", None)
        self.assertEqual(cy.main(root=t, hoje=HOJE), 1)
        self.assertIn("YOUTUBE_API_KEY ausente", manifesto(t, "youtube")["status"])

    def test_le_a_lista_de_envios_ate_a_data_inicial(self):
        t, pedidos = com_canal(), []

        def fake(recurso, params):
            pedidos.append((recurso, dict(params)))
            if recurso == "channels":
                return {"items": [{"id": "UCx", "snippet": {"title": "Fundación Disenso"}, "contentDetails": {"relatedPlaylists": {"uploads": "UUx"}}, "statistics": {"videoCount": "812", "subscriberCount": "150000"}}]}
            if recurso == "playlistItems":
                if not params.get("pageToken"):
                    return {"nextPageToken": "p2", "items": [{"contentDetails": {"videoId": "v1", "videoPublishedAt": "2026-09-01T10:00:00Z"}}, {"contentDetails": {"videoId": "v2", "videoPublishedAt": "2026-03-01T10:00:00Z"}}]}
                return {"nextPageToken": "p3", "items": [{"contentDetails": {"videoId": "v0", "videoPublishedAt": "2026-01-05T10:00:00Z"}}]}
            return {"items": [{"id": "v1", "snippet": {"title": "Debate  sobre España", "description": "Con @Santi_ABASCAL\n#Disenso", "publishedAt": "2026-09-01T10:00:00Z"}, "statistics": {"viewCount": "5000", "likeCount": "300"}, "contentDetails": {"duration": "PT10M"}}]}
        self.assertEqual(cy.main(buscar=fake, root=t, hoje=HOJE), 0)
        self.assertEqual(pedidos[0], ("channels", {"part": "snippet,contentDetails,statistics", "forHandle": "@fundaciondisenso"}))
        self.assertEqual([p[0] for p in pedidos].count("playlistItems"), 2)   # para na página inteira anterior ao período, sem ler a 3ª
        rows = list(csv.DictReader(gzip.open(t / "data/youtube/posts.csv.gz", "rt", encoding="utf-8"), delimiter=";"))
        self.assertEqual(len(rows), 1)                                         # v2 está na lista mas a API não devolveu (privado ou removido)
        r = rows[0]
        self.assertEqual((r["rede"], r["ator_id"], r["texto"], r["duracao_s"], r["visualizacoes"], r["comentarios"], r["url"]),
                         ("youtube", "disenso", "Debate sobre España — Con @Santi_ABASCAL #Disenso", "600", "5000", "", "https://www.youtube.com/watch?v=v1"))
        p = manifesto(t, "youtube")["perfis"][0]
        self.assertEqual((p["universo"]["posts_total_plataforma"], p["universo"]["seguidores"], p["lidos_no_periodo"], p["indisponiveis"]), (812, 150000, 1, 1))
        self.assertTrue(p["cobertura"].startswith("completa"))
        self.assertIn("disenso;Fundación Disenso;youtube;@fundaciondisenso;https://www.youtube.com/@fundaciondisenso;Fundación Disenso;150000;812", (t / "data/perfis/youtube_latest.csv").read_text(encoding="utf-8"))


RSS = """<?xml version="1.0"?><rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel>
<item><title>Foro Madrid en Chile</title><link>https://foromadrid.org/chile/</link><pubDate>Thu, 03 Sep 2026 10:00:00 +0200</pubDate><dc:creator>Redacción</dc:creator><category>Noticias</category><guid>https://foromadrid.org/?p=9</guid><description>resumen</description><content:encoded><![CDATA[<p>Texto íntegro</p>]]></content:encoded></item>
<item><title>Antiguo</title><link>https://foromadrid.org/antiguo/</link><pubDate>Mon, 05 Jan 2026 10:00:00 +0100</pubDate><guid>https://foromadrid.org/?p=1</guid></item>
</channel></rss>""".encode()


def fake_web(url):
    J = lambda o, **h: (200, h, json.dumps(o).encode())  # noqa: E731
    if url.endswith("/robots.txt"):
        return 200, {}, b"User-agent: *\nDisallow: /wp-admin/\n"
    if "fundaciondisenso.org" in url:
        if url.endswith("/types"):
            return J({"post": {"rest_base": "posts"}, "page": {"rest_base": "pages"}, "articulo": {"rest_base": "articulos"}})
        if "/categories" in url:
            return J([{"id": 3, "name": "An&aacute;lisis"}])
        if "per_page=1&" in url:
            return J([], **{"x-wp-total": "250" if "/posts" in url else "40"})
        if "page=1" in url and "/posts" in url:
            return J([{"id": 7, "date_gmt": "2026-10-01T08:00:00", "modified_gmt": "2026-10-02T08:00:00", "link": "https://fundaciondisenso.org/chile-en-jaque/", "type": "post",
                       "title": {"rendered": "Chile en &#8220;jaque&#8221;"}, "categories": [3], "yoast_head_json": {"author": "Analista"}, "excerpt": {"rendered": "<p>resumen</p>"}, "content": {"rendered": "<p>Texto íntegro del artículo</p>"}}],
                     **{"x-wp-total": "1", "x-wp-totalpages": "1"})
        if "page=1" in url:
            return J([], **{"x-wp-total": "3", "x-wp-totalpages": "1"})   # o site diz 3 no período e entrega 0: parcial
    if "foromadrid.org" in url:
        if "/feed/?paged=1" in url:
            return 200, {}, RSS
        return 404, {}, b""
    return 403, {}, b""   # voxespana.es recusa tudo


class TestSites(unittest.TestCase):
    def test_wp_json_rss_e_recusa(self):
        t, priv = projeto(), Path(tempfile.mkdtemp())
        os.environ["ATLAS_INTERNO_DIR"] = str(priv)
        try:
            self.assertEqual(cs.main(buscar=fake_web, root=t), 0)
        finally:
            del os.environ["ATLAS_INTERNO_DIR"]
        txt = gzip.open(t / "data/sites/artigos.csv.gz", "rt", encoding="utf-8").read()
        rows = {r["artigo_id"]: r for r in csv.DictReader(txt.splitlines(), delimiter=";")}
        self.assertEqual(sorted(rows), ["disenso:post:7", "foro-madrid:rss:https://foromadrid.org/?p=9"])   # o item de janeiro fica fora do período
        d = rows["disenso:post:7"]
        self.assertEqual((d["titulo"], d["categorias"], d["autor"], d["publicado_em"], d["via"]), ("Chile en “jaque”", "Análisis", "Analista", "2026-10-01T08:00:00Z", "wp-json"))
        f = rows["foro-madrid:rss:https://foromadrid.org/?p=9"]
        self.assertEqual((f["titulo"], f["publicado_em"], f["autor"], f["categorias"]), ("Foro Madrid en Chile", "2026-09-03T08:00:00Z", "Redacción", "Noticias"))
        self.assertNotIn("íntegro", txt)                                      # texto integral nunca vai ao público
        privado = "".join(gzip.open(p, "rt", encoding="utf-8").read() for p in (priv / "sites").glob("*.jsonl.gz"))
        self.assertIn("Texto íntegro del artículo", privado)
        m = json.loads((t / "data/sites/manifesto_latest.json").read_text(encoding="utf-8"))
        s = {x["site_id"]: x for x in m["sites"]}
        tipos = {x["tipo"]: x for x in s["disenso"]["tipos"]}
        self.assertEqual(sorted(tipos), ["articulo", "post"])                 # "page" é ignorado
        self.assertEqual((tipos["post"]["universo_total"], tipos["post"]["universo_no_periodo"], tipos["post"]["lidos"]), (250, 1, 1))
        self.assertTrue(tipos["post"]["cobertura"].startswith("completa"))
        self.assertTrue(tipos["articulo"]["cobertura"].startswith("parcial ⛔"))   # 0 lidos de 3 informados
        self.assertEqual((s["foro-madrid"]["via"], s["foro-madrid"]["tipos"][0]["universo_no_periodo"]), ("rss", None))   # RSS não informa total: nunca estimado
        self.assertIn("universo ⛔ desconhecido", s["foro-madrid"]["tipos"][0]["cobertura"])
        self.assertEqual((s["vox"]["cobertura"], s["vox"]["erro"]), ("⛔ não lido", "HTTP 403 no RSS (página 1)"))
        self.assertEqual(m["status"], "parcial: 1 site(s) não lido(s)")
        shutil.rmtree(priv)

    def test_robots_que_proibe_e_respeitado(self):
        t, vistos = projeto(), []

        def fake(url):
            vistos.append(url)
            return (200, {}, b"User-agent: *\nDisallow: /\n") if url.endswith("/robots.txt") else (200, {}, b"{}")
        self.assertEqual(cs.main(buscar=fake, root=t), 1)
        self.assertTrue(all(u.endswith("/robots.txt") for u in vistos))        # nenhum pedido além do robots.txt
        self.assertIn("robots.txt não permite", json.loads((t / "data/sites/manifesto_latest.json").read_text(encoding="utf-8"))["status"])


if __name__ == "__main__":
    unittest.main()
