import json, os, shutil, unittest
from pathlib import Path

from base import RAIZ, projeto
import collect_google_transparencia as cg
import collect_meta_anuncios_apify as cm


def com_config():
    t = projeto()
    for f in ("google_transparencia.json", "meta_anuncios.json", "temas.json"):
        shutil.copy(RAIZ / "data/config" / f, t / "data/config" / f)
    return t


class TestGoogle(unittest.TestCase):
    def test_nome_curto_so_casa_por_inteiro_e_regiao_vem_da_config(self):
        t = com_config()
        ac = json.loads((t / "data/config/google_transparencia.json").read_text(encoding="utf-8"))["anunciantes_aceitos"]

        def fake(cfg):
            sugs = [{"nome": "VOX", "id": "AR1", "pais": "ES"}, {"nome": "Vox Media LLC", "id": "AR2", "pais": "ES"}, {"nome": "Fundación Disenso", "id": "AR3", "pais": "ES"}, {"nome": "VOX", "id": "AR4", "pais": "BR"}]
            an = {s["id"]: {"advertiser_id": s["id"], "nome": s["nome"], "encontrado_por": "t"} for s in sugs if cg.aceitar(s, ac)}
            cr = [{"creative_id": "C1", "advertiser_id": "AR1", "anunciante": "VOX", "dominio": "voxespana.es", "formato": "vídeo", "primeira_exibicao": "2026-11-01", "ultima_exibicao": "2026-11-14", "origem": "anunciante:AR1", "url": "u", "previa": None},
                  {"creative_id": "C0", "advertiser_id": "AR3", "anunciante": "Fundación Disenso", "dominio": "fundaciondisenso.org", "formato": "imagem", "primeira_exibicao": "2024-05-01", "ultima_exibicao": "2024-06-01", "origem": "anunciante:AR3", "url": "u", "previa": None}]
            return an, cr, []
        self.assertEqual(cg.main([str(t)], coletar_fn=fake), 0)
        d = json.loads((t / "data/google_ads/transparencia.json").read_text(encoding="utf-8"))
        self.assertEqual([a["advertiser_id"] for a in d["anunciantes"]], ["AR1"])          # "Vox Media" e o VOX de outro país ficam fora; Disenso só tem anúncio antigo
        self.assertEqual((d["anunciantes"][0]["exibidos_na_campanha"], d["anunciantes"][0]["url"]), (1, "https://adstransparency.google.com/advertiser/AR1?region=ES"))
        self.assertEqual((d["fora_do_recorte"]["anuncios"], d["fora_do_recorte"]["anunciantes"]), (1, ["Fundación Disenso"]))


class TestMeta(unittest.TestCase):
    def test_busca_em_todos_os_anuncios_da_espanha_com_teto(self):
        t, pedidos, aqui = com_config(), [], os.getcwd()
        os.chdir(t)
        try:
            def fake(payload, cap):
                pedidos.append((payload, cap))
                return {"id": "r", "status": "SUCCEEDED", "usageTotalUsd": 0.001}, ([{"ad_archive_id": "9", "page_id": "1", "page_name": "Tienda X", "start_date": 1790000000, "publisher_platform": ["facebook"]}] if "Abascal" in payload["adLibraryUrls"][0] else [])
            self.assertEqual(cm.main(["--teste"], executar=fake), 0)
        finally:
            os.chdir(aqui)
        url = pedidos[0][0]["adLibraryUrls"][0]
        self.assertIn("ad_type=all", url)
        self.assertIn("country=ES", url)
        self.assertEqual((len(pedidos), pedidos[0][1], pedidos[0][0]["minDate"]), (4, 0.1, "2026-02-16"))   # 4 consultas dividem o teto de US$ 0,40
        d = json.loads((t / "data/meta/anuncios.json").read_text(encoding="utf-8"))
        self.assertEqual((d["consultas"]["abascal"]["anuncios"], d["consultas"]["vox"]["anuncios"], d["custo_usd"]), (1, 0, 0.004))
        self.assertNotIn("ad_creative", (t / "data/meta/anuncios_apify.csv").read_text(encoding="utf-8"))   # sem texto de anúncio no público


if __name__ == "__main__":
    unittest.main()
