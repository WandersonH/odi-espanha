import json, shutil, unittest

from base import RAIZ, projeto
import collect_telegram as ct
import comum

PAG = '''<div class="tgme_channel_info_header_title"><span dir="auto">VOX 🇪🇸</span></div>
<div class="tgme_channel_info_counter"><span class="counter_value">95.4K</span> <span class="counter_type">subscribers</span></div>
<div class="tgme_widget_message js-widget_message" data-post="VOXtelegram/{a}"><div class="tgme_widget_message_text js-message_text" dir="auto">Con <b>Bolsonaro</b> en Madrid<br/>2ª línea &amp; más</div>
<span class="tgme_widget_message_views">12.3K</span><a class="tgme_widget_message_date" href="x"><time datetime="{da}T10:00:00+00:00" class="time">10:00</time></a></div>
<div class="tgme_widget_message js-widget_message" data-post="VOXtelegram/{b}"><a class="tgme_widget_message_video_player"></a>
<span class="tgme_widget_message_views">900</span><a class="tgme_widget_message_date" href="x"><time datetime="{db}T09:00:00+00:00" class="time">09:00</time></a></div>'''


def config(t):
    """Configuração fixa do teste (um canal): o teste não depende dos canais cadastrados no projeto."""
    shutil.copy(RAIZ / "data/config/temas.json", t / "data/config/temas.json")
    (t / "data/config/telegram.json").write_text(json.dumps({"nota": "teste", "intervalo_s": 0, "max_paginas": 50,
        "canais": [{"ator_id": "vox", "ator_nome": "Vox", "canal": "VOXtelegram", "url": "https://t.me/VOXtelegram", "confirmado": True}]}), encoding="utf-8")


class TestTelegram(unittest.TestCase):
    def test_parse(self):
        ms, canal = ct.parse(PAG.format(a=12, da="2026-09-02", b=11, db="2026-09-01"))
        self.assertEqual((canal["inscritos"], canal["nome_exibido"]), (95400, "VOX 🇪🇸"))
        self.assertEqual([(m["n"], m["publicado_em"], m["visualizacoes"], m["tipo"]) for m in ms], [(12, "2026-09-02T10:00:00Z", 12300, "texto"), (11, "2026-09-01T09:00:00Z", 900, "vídeo")])
        self.assertEqual(ms[0]["texto"], "Con Bolsonaro en Madrid\n2ª línea & más")

    def test_le_ate_a_data_inicial_e_nao_inventa_universo(self):
        t = projeto()
        config(t)
        pedidos = []

        def buscar(u):
            pedidos.append(u)
            return PAG.format(a=12, da="2026-09-02", b=11, db="2026-09-01") if "before" not in u else PAG.format(a=10, da="2026-02-20", b=9, db="2026-01-05")
        self.assertEqual(ct.main(root=t, buscar=buscar), 0)
        self.assertEqual(pedidos, ["https://t.me/s/VOXtelegram", "https://t.me/s/VOXtelegram?before=11"])
        k = json.loads((t / "data/telegram/resumo.json").read_text(encoding="utf-8"))["canais"][0]
        self.assertEqual((k["no_acervo"], k["universo_mensagens"], k["maior_numero_de_mensagem"], k["citam_o_brasil"], k["inscritos"], k["mensagem_mais_recente_do_canal"]), (3, None, 12, 2, 95400, "2026-09-02T10:00:00Z"))   # a de 05/01 fica fora do período
        self.assertTrue(k["cobertura"].startswith("completa"))
        self.assertEqual(len(comum.ler_acervo(t / "data/telegram/posts.csv.gz")), 3)

    def test_erro_de_rede_nao_vira_completa(self):
        t = projeto()
        config(t)

        def cai(u):
            raise OSError("sem rede")
        self.assertEqual(ct.main(root=t, buscar=cai), 1)
        self.assertEqual(json.loads((t / "data/telegram/resumo.json").read_text(encoding="utf-8"))["canais"][0]["cobertura"], "⛔ não lido")


if __name__ == "__main__":
    unittest.main()
