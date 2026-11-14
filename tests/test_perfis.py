import datetime as dt, json, os, shutil, tempfile, unittest
from pathlib import Path

from base import manifesto, projeto
import collect_perfis as cp

HOJE = dt.date(2026, 11, 14)
RUN = {"id": "r", "status": "SUCCEEDED", "usageTotalUsd": 0.01}


def fake(ator, payload, cap):
    if "instagram" in ator:
        return RUN, [{"username": u, "fullName": u.upper(), "verified": True, "private": False, "followersCount": 1000, "postsCount": 321, "biography": "bio"} for u in payload["usernames"]]
    if "facebook" in ator:
        return RUN, [{"pageUrl": p["url"] + "/", "title": "Página", "followers": 2000} for p in payload["startUrls"]]
    return RUN, [{"type": "tweet", "id": "1", "author": {"userName": q[5:], "name": "Nome", "followers": 3000, "statusesCount": 400, "description": "bio"}} for q in payload["searchTerms"]]


class TestPerfis(unittest.TestCase):
    def test_sem_autorizacao(self):
        t = projeto()
        self.assertEqual(cp.main(["--diario"], executar=fake, root=t, hoje=HOJE), 1)
        self.assertIn("sem autorização", manifesto(t, "perfis")["status"])

    def test_diario_grava_universo_dos_confirmados(self):
        t = projeto(perfis_teto={"diario": {"teto_dia_usd": 0.2, "teto_mes_usd": 2.0}})
        self.assertEqual(cp.main(["--diario"], executar=fake, root=t, hoje=HOJE), 0)
        csv_ = (t / "data/perfis/latest.csv").read_text(encoding="utf-8").splitlines()
        self.assertEqual(csv_[0], "ator_id;ator_nome;rede;perfil;url;nome_exibido;seguidores;posts_total;verificado;captured_at;fonte")
        self.assertEqual(len(csv_), 3)                                    # Vox no Instagram e no Facebook: só os confirmados
        self.assertIn("vox;Vox;instagram;vox_es;https://www.instagram.com/vox_es/;VOX_ES;1000;321;sim;", csv_[1])
        self.assertIn("vox;Vox;facebook;vox.espana;https://www.facebook.com/vox.espana;Página;2000;;", csv_[2])  # o Facebook não informa total de posts: vazio, não zero
        self.assertEqual(manifesto(t, "perfis")["custo_usd"], 0.02)

    def test_sonda_ficha_de_candidato_so_no_privado(self):
        t = projeto(perfis_teto={"sonda": {"teto_usd": 0.5}})
        self.assertEqual(cp.main(["--sonda"], executar=fake, root=t, hoje=HOJE), 0)   # sem privado: candidatos não são sondados
        m = manifesto(t, "perfis")
        self.assertEqual((m.get("candidatos_sondados"), m["candidatos_nao_sondados"] > 0), (0, True))
        self.assertTrue(all(p["confirmado"] for p in m["perfis"]))
        priv = Path(tempfile.mkdtemp())
        os.environ["ATLAS_INTERNO_DIR"] = str(priv)
        try:
            t2 = projeto(perfis_teto={"sonda": {"teto_usd": 0.5}})
            self.assertEqual(cp.main(["--sonda"], executar=fake, root=t2, hoje=HOJE), 0)
        finally:
            del os.environ["ATLAS_INTERNO_DIR"]
        publico = json.loads((t2 / "data/perfis/sonda.json").read_text(encoding="utf-8"))
        self.assertTrue(publico["perfis"] and all(p["confirmado"] for p in publico["perfis"]))
        ficha = json.loads(next((priv / "perfis").glob("sonda_candidatos_*.json")).read_text(encoding="utf-8"))
        self.assertIn("ecader", {p["perfil"] for p in ficha})
        tudo_publico = "".join(p.read_text(encoding="utf-8") for p in (t2 / "data/perfis").glob("*.json"))
        self.assertNotIn("ecader", tudo_publico)                           # nome, bio e números do candidato não vão ao público
        self.assertNotIn("foromadrid_", tudo_publico)
        shutil.rmtree(priv)


if __name__ == "__main__":
    unittest.main()
