import csv, gzip, json, os, re, tempfile, unittest
from pathlib import Path

from base import RAIZ, projeto
import carregar_area_pesquisador as c
import comum


def acervo(t, rede, linhas):
    ac = {}
    for pid, ator, perfil, texto in linhas:
        ac[pid] = {**{k: "" for k in comum.COLS}, "post_id": pid, "ator_id": ator, "ator_nome": ator.title(), "rede": rede, "perfil": perfil, "publicado_em": "2026-09-01T10:00:00Z", "texto": texto}
    comum.gravar_acervo(t / "data" / rede / "posts.csv.gz", ac)


class TestCarga(unittest.TestCase):
    def setUp(self):
        self.t, self.priv = projeto(), Path(tempfile.mkdtemp())
        acervo(self.t, "x", [("1", "vox", "vox_es", "España 🔥"), ("2", "abascal", "Santi_ABASCAL", "  "), ("3", "abascal", "Santi_ABASCAL", "Hola")])
        d = self.priv / "youtube/comentarios"
        d.mkdir(parents=True)
        with gzip.open(d / "comentarios.csv.gz", "wt", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, ["comentario_id", "video_id", "ator_id", "resposta_a", "autor", "autor_canal_id", "texto", "publicado_em"], delimiter=";", lineterminator="\n")
            w.writeheader()
            w.writerow({"comentario_id": "c1", "video_id": "v", "ator_id": "vox", "autor": "Fulana de Tal", "autor_canal_id": "UCsecreto", "texto": "linha um\nlinha dois", "publicado_em": "2026-09-02T00:00:00Z"})
        self.antigo = {k: os.environ.pop(k, None) for k in ("ATLAS_INTERNO_DIR", "ODI_INTERNO_DIR", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY")}

    def tearDown(self):
        for k, v in self.antigo.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)

    def test_comentario_nunca_leva_autor_e_caso_e_o_ator(self):
        ls = list(c.linhas(self.t, self.priv))
        self.assertEqual([(r["caso"], r["fonte"], r["item_id"], r["autor"]) for r in ls], [("vox", "post", "1", "@vox_es"), ("abascal", "post", "3", "@Santi_ABASCAL"), ("vox", "comentario", "c1", None)])
        self.assertEqual(ls[0]["emojis"], ["🔥"])
        self.assertNotIn("Fulana", json.dumps(ls, ensure_ascii=False))
        self.assertNotIn("UCsecreto", json.dumps(ls, ensure_ascii=False))
        self.assertEqual({tuple(sorted(r)) for r in ls}, {tuple(sorted(ls[0]))})          # mesmas chaves em todas as linhas (exigência do envio em lote)

    def test_seco_nao_envia_e_sem_privado_so_publicacoes(self):
        enviados = []
        self.assertEqual(c.main(["--seco"], enviar_fn=enviados.append, root=self.t), 0)   # sem privado no ambiente: só as 2 publicações com texto
        self.assertEqual(enviados, [])
        os.environ["ATLAS_INTERNO_DIR"] = str(self.priv)
        self.assertEqual(c.main(["--caso", "vox"], enviar_fn=enviados.append, root=self.t), 0)
        self.assertEqual([(r["fonte"], r["item_id"]) for lote in enviados for r in lote], [("post", "1"), ("comentario", "c1")])

    def test_sem_chave_nao_tenta_enviar(self):
        self.assertEqual(c.main([], root=self.t), 1)


class TestBancoEPagina(unittest.TestCase):
    def test_toda_tabela_publica_tem_rls_e_anon_nao_le(self):
        sql = "\n".join(f.read_text(encoding="utf-8") for f in sorted((RAIZ / "supabase/migrations").glob("*.sql")))
        tabelas = set(re.findall(r"create table if not exists public\.(\w+)", sql))
        self.assertTrue({"corpus", "pesquisadores", "acessos", "avaliacoes", "amostra_validacao"} <= tabelas)
        for t in tabelas:
            self.assertRegex(sql, rf"alter table public\.{t} enable row level security", t)
        self.assertNotRegex(sql, r"to anon\b(?! *,? *authenticated)")                       # nenhuma política ou permissão só para anônimo

    def test_pagina_aponta_para_o_projeto_da_espanha_e_nao_guarda_chave(self):
        s = (RAIZ / "area-pesquisador.html").read_text(encoding="utf-8")
        self.assertIn("https://zlrzraqngiszsgoedlfv.supabase.co/functions/v1/odi-area-config", s)
        self.assertNotIn("vidnoyzechknrqhczmrr", s)
        for proibido in ("eyJhbGciOi", "sb_secret_", "sb_publishable_", "service_role"):
            self.assertNotIn(proibido, s)
        wf = (RAIZ / ".github/workflows/area-pesquisador.yml").read_text(encoding="utf-8")
        self.assertIn("secrets.SUPABASE_SERVICE_ROLE_KEY_ESP", wf)

    def test_indice_de_casos_segue_os_atores(self):
        at = json.loads((RAIZ / "data/config/atores.json").read_text(encoding="utf-8"))
        ids = [a["id"] for a in (at["atores"] if isinstance(at, dict) else at)]
        self.assertEqual([x["id"] for x in json.loads((RAIZ / "data/casos/indice.json").read_text(encoding="utf-8"))["casos"]], ids)
        for f in ("data/config/livro_codigos_validacao.json", "assets/odi-concordancia.js", "supabase/functions/odi-area-config/index.ts"):
            self.assertTrue((RAIZ / f).exists(), f)


if __name__ == "__main__":
    unittest.main()
