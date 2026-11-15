# CHANGELOG

## E1.28 — 15/11/2026 · Rede de coocorrência; gráfico mensal do Panorama e seguidores do X corrigidos

**Correções de erros meus.**

- **Gráfico "Publicações por mês e por rede" (Panorama) desmontado** desde a E1.10: a barrinha nova das telas usava o mesmo nome de estilo (`esp-barra`) do gráfico antigo e o desfigurou (rótulos riscados, barra uma linha abaixo do mês). A barrinha nova passou a se chamar `esp-medidor`.
- **Seguidores do X apagados para 4 perfis** (Vox, Abascal, Foro Madrid, Martín Frías) desde o run 43755154891: a carga só de `FDisenso` e `ecader` regravou `data/perfis/x_latest.csv` com dois perfis. `collect_x_posts.depois` agora soma ao arquivo existente; os quatro números foram restaurados da versão do commit 12c72db (leitura de 15/11/2026, run 43740489231). Teste novo cobre o caso.
- **Série mensal de comentários:** barras relativas ao maior ator escondiam os menores; agora cada ator tem a própria escala, e mês com zero não mostra traço.

**Novo: rede de coocorrência** (`scripts/build_rede_coocorrencia.py`), método do ODI Atlas (`build_rede.py`) para seis atores: nó = palavra ou #tag em 8+ publicações (até 150), aresta = mesma publicação (peso mínimo 3, até 8 por nó), Louvain e ForceAtlas2 com semente fixa. Saídas por rede: `rede.json`, `rede.gexf` (Gephi), `rede_nos.csv`, `rede_arestas.csv`, `rede_publicacoes_termos.csv`. Na página, caderno "O que dizem": desenho com cor por comunidade, clique para isolar um termo, tabela de comunidades e downloads. Diferença do original: a opção `distributed_action` (o "dissuade hubs" do Gephi) foi desligada, porque empurrava os termos mais frequentes para os cantos. A rede passou a rodar nos dois workflows (networkx 3.6.1, mesma versão do ODI Atlas).

**O que foi realmente executado.** `python scripts/build_rede_coocorrencia.py` no acervo local: Instagram 150 nós, 1.051 arestas, 6 comunidades, modularidade 0,244; X 150, 1.070, 4, 0,247; Facebook 150, 970, 6, 0,353; YouTube 150, 830, 6, 0,379. Página aberta em navegador sem interface: gráfico mensal correto, seguidores do X com os seis perfis, rede desenhada nas quatro redes, sem erro de console. `python -m unittest discover -s tests` → 64 testes, OK.

## E1.27 — 15/11/2026 · Correção: teste do Telegram dependia da configuração real

**O que aconteceu.** O commit d1a42c7 (E1.26) foi enviado com um teste falhando: `test_telegram` copiava `data/config/telegram.json` do projeto e quebrou quando entraram dois canais. O run 43766888293 parou no passo de testes e o Telegram não foi lido. A entrada E1.26 diz "62 testes, OK" e isso estava errado: eram 61 passando e 1 falhando; a verificação do comando não olhava o código de saída.

**O que mudou.** `tests/test_telegram.py` usa configuração própria, fixa. Nenhuma mudança no coletor.

**O que foi realmente executado.** `python -m unittest discover -s tests` → 62 testes, OK, conferido pelo código de saída. A leitura dos canais está na entrada seguinte.

## E1.26 — 15/11/2026 · Primeira leitura de "Em alta agora" e do Google Notícias; mais dois canais do Telegram

**O que foi realmente executado.** Run 43766518449 (`trends.yml`): "Em alta agora" na Espanha com 10 buscas na leitura de 2026-11-15T22:00:31Z, nenhuma citando os atores; Google Notícias com 20 resultados, 5 para cada um dos 4 termos. Arquivos: `data/trends/agora.json`, `data/trends/noticias.json` e os dois históricos em CSV. O Trends por termo foi relido na mesma execução (9 consultas).

**O que mudou e por quê.** `data/config/telegram.json`: canais `foromadrid` (Foro Madrid) e `fdisenso` (Fundación Disenso), endereços enviados pelo responsável. A leitura deles está na entrada seguinte.

**Testes.** `python -m unittest discover -s tests` → 62 testes, OK.

## E1.25 — 15/11/2026 · "Em alta agora", Google Notícias e linha do tempo de cada vídeo

**O que mudou e por quê.** O responsável cobrou os dois blocos do caderno de buscas que tinham ficado como "ainda não trazido" e a linha do tempo dos vídeos do YouTube.

- `scripts/collect_trends_agora.py` + passo em `trends.yml`: "Em alta agora" na Espanha e os 5 primeiros resultados do Google Notícias por termo, pelos RSS públicos do Google. É uma versão enxuta do coletor do ODI Atlas, sem a parte dos debates. Grava a leitura e um histórico por dia.
- `data/config/trends.json`: `noticias_termos` (Vox, Santiago Abascal, Fundación Disenso, Foro Madrid).
- `index.html`: os dois blocos no caderno de buscas; no caderno "O que dizem", nova linha do tempo com uma bolha por publicação (no YouTube, por vídeo), área pela audiência e clique que abre o vídeo. O caderno passa a abrir no YouTube, como no original.

**O que foi realmente executado.** `python -m unittest discover -s tests` → 62 testes, OK; `node --check`; página aberta em navegador sem interface com os dados do repositório: "O que dizem" abre no YouTube e desenha uma bolha por vídeo, sem erro de console. A coleta real está na entrada seguinte.

**Pendente.** Gráfico normal × pico. A lista "em alta" é lida uma vez por dia; no original era de hora em hora.

## E1.24 — 15/11/2026 · Termos do glossário de política espanhola testados no dicionário de temas

**O que mudou e por quê.** O responsável indicou `https://www.politicaelectoral.com/es/espana/glosario` (437 termos, sem licença de reuso declarada). Só os nomes de termos de nove categorias foram usados, como candidatos; nenhuma definição foi copiada. Cada candidato foi contado no acervo, e entraram em `data/config/temas.json` os que aparecem em 3 publicações ou mais e ainda não constavam (entre parênteses, o número de publicações):

- `adversarios`: sanchismo (6)
- `nacion_unidad`: amnistia (4), separatismo (8)
- `familia_valores`: solo si es si (3)
- `seguridad`: uco (25)
- `vivienda`: vivienda protegida (7)

**O que foi realmente executado.** Contagem sobre as 8490 publicações de Instagram, X, Facebook e YouTube do acervo local: com ao menos um tema, 5800 → 5812 (68.3% → 68.5%); que citam adversário, 2379 → 2379. `python -m unittest discover -s tests` → 59 testes, OK. Os arquivos da página são regerados na próxima execução das análises.

**Pendente.** O dicionário continua rascunho, a validar pelos pesquisadores. Só uma parte do glossário foi testada (as categorias exibidas na página principal).

## E1.23 — 15/11/2026 · Instagram de Cader é privado; Similarweb da Disenso completado

**O que foi realmente executado.** Run 43762406629 (`coleta.yml`, carga, Instagram, `ecader`): o coletor devolveu um único item com o aviso `private`. O perfil é privado; nenhuma publicação foi lida. O manifesto registra o custo dessa tentativa.

**O que mudou e por quê.**

- `data/config/atores.json`: Instagram `ecader` sai da coleta, com a nota de que é privado (o projeto só lê conteúdo público). Facebook `ecader` fica confirmado e não coletado, à espera do teto.
- `data/config/coleta.json`: teto da carga do Facebook de volta a US$ 5,80; o aumento para US$ 6,15 não foi usado.
- `scripts/comum.py`: quando o ator devolve só um aviso de erro e nada é lido, a cobertura passa a ser "⛔ não lido". Antes saía "completa", o que estava errado.
- `data/config/sites_audiencia.json`: Similarweb de fundaciondisenso.org completado com a segunda captura enviada pelo responsável (duração média 00:00:50, rejeição 55,74%, variação +20,63%, países, canais, origem).

**Testes.** `python -m unittest discover -s tests` → 59 testes, OK.

**Pendente.** Teto do Facebook para `SantiagoAbascalConde` e `ecader`.

## E1.22 — 15/11/2026 · Instagram e Facebook de Eduardo Cader confirmados

**O que mudou e por quê.** O responsável enviou `https://www.instagram.com/ecader/` e `https://www.facebook.com/ecader`. `data/config/atores.json`: os dois perfis passam de "não localizado" a confirmados, com o envio do responsável como fonte. `data/config/coleta.json`: teto da carga do Instagram de US$ 0,35 para US$ 0,40 e do Facebook de US$ 5,80 para US$ 6,15, só para este perfil, com a frase de autorização.

**O que foi realmente executado.** `python -m unittest discover -s tests` → 59 testes, OK. As cargas estão na entrada seguinte.

## E1.21 — 15/11/2026 · Telegram do Vox: uma mensagem só, de 07/11/2025

**O que foi realmente executado.** Run 43760463042 (`gratuitas.yml`, opção `telegram`): `VOXtelegram` tem 840 inscritos e a prévia pública mostra uma única mensagem, a de número 1, de 07/11/2025. Não há mensagens no período do estudo (desde 16/02/2026). Evidência: `data/telegram/resumo.json` e `data/telegram/manifesto_latest.json`.

**Pendente.** Confirmar com o responsável se existe outro canal do Vox em uso; este é o que o site voxespana.es divulga, mas está parado.

## E1.20 — 15/11/2026 · Primeira leitura do Telegram: canal sem mensagens no período

**O que foi realmente executado.** Run 43760163532 (`gratuitas.yml`, opção `telegram`): canal `VOXtelegram` lido; o Telegram informa 840 inscritos; a primeira página da prévia já só tem mensagens anteriores a 16/02/2026, então há 0 mensagens no período. As capturas de Semrush e Similarweb (7 arquivos, 15 MB) foram gravadas no repositório privado em `evidencias/sites_audiencia/2026-11-15/`.

**O que mudou e por quê.** A leitura não guardava a data da mensagem mais recente do canal, que é justamente o dado que explica o zero. `collect_telegram.py` passa a registrar a mensagem mais recente e a mais antiga vistas; a tela mostra essa data quando não há mensagens no período; canal sem mensagens no período deixa de ser tratado como falha.

**Testes.** `python -m unittest discover -s tests` → 59 testes, OK. A nova leitura está na entrada seguinte.

## E1.19 — 15/11/2026 · Telegram (canais públicos) e audiência estimada dos sites

**O que mudou e por quê.** O responsável mandou o canal `https://t.me/VOXtelegram` e sete capturas de tela (Semrush e Similarweb) dos três sites oficiais.

- `scripts/collect_telegram.py` + `data/config/telegram.json` + passo em `gratuitas.yml`: mensagens de canais públicos pela prévia do próprio Telegram na web (t.me/s), sem login e sem custo, até a data inicial do período. O Telegram não informa o total de mensagens: o universo fica ⛔ e o maior número de mensagem aparece só como teto.
- `index.html`: caderno "Telegram · canais públicos" (inscritos, lidas no período, cobertura, por mês, últimas mensagens, etiqueta "cita o Brasil") e bloco "Audiência estimada dos sites" no caderno de sites.
- `data/config/sites_audiencia.json`: números transcritos das capturas, como exibidos, com ferramenta, recorte e data. São estimativas de terceiros. Semrush lido da imagem; Similarweb lido por reconhecimento de texto das capturas. A duração média da visita de fundaciondisenso.org não saiu legível e está como ⛔. As variações mensais do Similarweb não foram transcritas porque o sinal não ficou legível.
- O Telegram ainda não entra em "O que dizem" nem na planilha geral de "cita o Brasil"; tem contagem própria no caderno dele.

**O que foi realmente executado.** `python -m unittest discover -s tests` → 59 testes, OK; `node --check` no script da página. A leitura real do canal está na entrada seguinte.

## E1.18 — 15/11/2026 · Primeira coleta do Google Trends da Espanha; YouTube de Abascal lido

**O que foi realmente executado.**

- Run 43759045300 (`trends.yml`): 9 consultas com status ok (3 grupos × 3 períodos), coleta de 15/11/2026 20:36 UTC, em `data/trends/2026-11-15/203644/` e `data/trends/caderno.json`. Os tópicos foram encontrados: Vox como "Partido político" e Santiago Abascal como "Diputado en el Congreso de los Diputados de España". Pontos por série: 169 (7 dias), 93 (3 meses) e 40 (período do estudo, que o Google devolveu por semana). Recorte regional: 19 linhas (17 comunidades autónomas, Ceuta e Melilla). Consultas relacionadas só no grupo de tópicos.
- Na consulta de tópicos do período do estudo, o máximo (100) é de Abascal na semana de 08/11/2026, quando o tópico Vox marcou 40. "Fundación Disenso", "Jorge Martín Frías" e "Eduardo Cader" ficaram em 0 em todas as janelas: sem volume suficiente para o Google mostrar.
- Run 43759047498 (`gratuitas.yml`): YouTube `@Santi_ABASCAL` com universo de 208 vídeos, 47 no período, cobertura completa; comentários desses vídeos: universo 3.276, lidos 3.276. Acervo total: 8.490 publicações; comentários guardados no privado: 203.638.
- Página: caderno de buscas aberto em navegador sem interface com o arquivo real: 30 linhas de série, 9 tabelas regionais, sem erro de console.

**Correção.** O rótulo do período do estudo dizia "dia a dia"; a série veio semanal. Rótulo e nota de configuração corrigidos.

**Pendente.** "Em alta agora", Google Notícias e gráfico normal × pico; termos do Trends a confirmar pelos pesquisadores.

## E1.17 — 15/11/2026 · Google Trends da Espanha (coletor do ODI Atlas) e canal de Abascal no YouTube

**O que mudou e por quê.** O responsável perguntou por que as buscas da Espanha não tinham sido feitas e mandou o canal `https://www.youtube.com/@Santi_ABASCAL`.

- `scripts/collect_trends.py` e `scripts/build_trends_caderno.py`: cópias do ODI Atlas; mudam só região (ES), idioma da interface (espanhol), fuso (Madri) e o prefixo das regiões.
- `data/config/trends.json`: três grupos (tópicos de Vox e Abascal; os atores como termos de busca; as pessoas como termos de busca), períodos de 7 dias, 3 meses e o período do estudo dia a dia. Termos a confirmar pelos pesquisadores.
- `.github/workflows/trends.yml`: manual e diário.
- `index.html`, caderno "Buscas · Google Trends": série por consulta, tabela por comunidade autónoma e consultas relacionadas, lendo `data/trends/caderno.json`. Sem arquivo, continua ⛔.
- `data/config/atores.json`: YouTube de Santiago Abascal (`@Santi_ABASCAL`), endereço informado pelo responsável.

**Não trazido:** "Em alta agora", Google Notícias e o gráfico normal × pico.

**O que foi realmente executado.** `python -m unittest discover -s tests` → 56 testes, OK; `node --check` no script da página. A coleta real está na entrada seguinte.

## E1.16 — 15/11/2026 · Facebook da Disenso recuperado sem novo gasto; números da etiqueta "cita o Brasil"

**O que foi realmente executado.**

- Run 43757160974 (`recuperar-bruto.yml`, sem custo): a execução do Facebook que tinha falhado com `IncompleteRead` existia na Apify, com 179 itens; foi copiada para o repositório privado, junto com o bruto das cargas de X e Instagram desta tarde (3.608 itens no total).
- Run 43757302240 (`coleta.yml`, carga, Facebook, `fundaciondisenso`, opção recuperar): 179 publicações no período, cobertura completa (a leitura parou pela data inicial; pedido 249). Nada foi rodado de novo; o custo da execução original entrou no manifesto. Acervo do Facebook: 823.
- Run 43757519360 (`coleta.yml`, sonda de perfis): seguidores e total de publicações dos perfis novos.
- Etiqueta "cita o Brasil", gerada nos runs acima (`data/site/cita_brasil.json` e `.csv`): 23 publicações em 8.441. Por rede: X 15, Instagram 4, Facebook 4, YouTube 0. Por ator: Fundación Disenso 8, Foro Madrid 6, Santiago Abascal 4, Vox 3, Jorge Martín Frías 2, Eduardo Cader 0.

**Universo e amostra dos perfis novos** (`data/site/resumo.json`): X `FDisenso` 6.846 publicações desde a criação, 498 no período; X `ecader` 17.841 e 17; Instagram `santi_abascal` 6.997 e 372; Facebook `fundaciondisenso` universo ⛔ não informado pela plataforma, 179 no período. Todas com cobertura completa do período. Acervo total: 8.441 publicações, 18 perfis confirmados.

**Pendente.** Facebook `SantiagoAbascalConde`: confirmado, não coletado, à espera de teto. Etiqueta "cita o Brasil" nos comentários do YouTube e nos títulos dos sites.

## E1.15 — 15/11/2026 · Cargas dos perfis confirmados; recuperação que nunca paga duas vezes

**O que foi realmente executado (workflow `coleta.yml`, modo carga, só os perfis novos).**

- Run 43755154891, X: `FDisenso` 498 publicações no período e `ecader` 17, as duas com cobertura completa (a leitura parou pela data inicial). Acervo do X: 3.887.
- Run 43755386153, Instagram: `santi_abascal` 372 publicações no período, cobertura completa (1.703 itens lidos; o restante é de fora do período ou de outra conta). Acervo do Instagram: 2.515.
- Run 43756590226, Facebook: `fundaciondisenso` ⛔ não lido (`IncompleteRead` na chamada à Apify). A execução pode ter sido feita e cobrada sem que o resultado chegasse; o custo dela não está no manifesto.

**O que mudou e por quê.**

- `scripts/comum.py`: `--recuperar` agora procura primeiro a execução guardada no repositório privado (por `recuperar_bruto.py`) que ainda não está em nenhum manifesto e cujos itens são do perfil, e **nunca roda de novo**. Antes, se não achasse a execução pela comparação do pedido, rodava outra vez e pagava de novo; foi o que aconteceu com o `vox_es` do Instagram.
- `data/config/atores.json`: Facebook `SantiagoAbascalConde` confirmado pelo responsável. Não foi coletado: o teto do Facebook não comporta essa página sem nova autorização.

**Testes.** `python -m unittest discover -s tests` → 55 testes, OK.

**Pendente.** Recuperar a execução do Facebook da Disenso (próxima entrada); teto para o Facebook de Abascal.

## E1.14 — 15/11/2026 · Etiqueta "cita o Brasil"

**O que mudou e por quê.** O responsável pediu: "classificar com uma etiqueta de cita o Brasil tudo que citar Brasil, Lula ou Flávio Bolsonaro e sua família".

- `data/config/temas.json`: lista `cita_brasil` (brasil*, brazil*, lula e formas listadas, bolsonaro*, e os endereços de Jair, Flávio, Eduardo, Carlos e Michelle Bolsonaro) e nota de método. Regra por palavra, sem IA. Não diz se a citação é favorável ou crítica.
- `scripts/texto.py`, `scripts/build_o_que_dizem.py`: cada publicação ganha `cita_brasil` e `brasil_termos` (o que foi encontrado, para conferência); cada ator ganha a contagem.
- `scripts/exportar_cita_brasil.py`: `data/site/cita_brasil.csv` (planilha de conferência, todas as redes) e `data/site/cita_brasil.json`. Entrou no passo de análises dos dois workflows.
- `index.html`, caderno "O que dizem": coluna "Cita o Brasil", filtro "citam o Brasil" (lista até 40 por ator, da mais recente para a mais antiga), marca em cada publicação e link da planilha.
- Um teste pegou falso positivo de `lula*` (casava qualquer palavra começada por "lula"); a regra ficou em "lula" como palavra inteira mais formas listadas.

**O que foi realmente executado.** `python -m unittest discover -s tests` → 54 testes, OK. `python scripts/build_o_que_dizem.py && python scripts/exportar_cita_brasil.py` na cópia local do acervo, antes das cargas dos perfis confirmados hoje: 15 publicações com a etiqueta em 7.375 (X 11, Instagram 3, Facebook 1, YouTube 0). Os arquivos locais foram descartados; os números publicados saem da próxima execução no GitHub e estão na entrada seguinte.

**Pendente.** A etiqueta vale para as publicações dos perfis. Não foi aplicada aos comentários do YouTube nem aos títulos dos artigos dos sites.

## E1.13 — 15/11/2026 · Quatro perfis confirmados pelo responsável entram na coleta

**O que mudou e por quê.** O responsável abriu e confirmou quatro endereços que estavam como "candidato a conferir" e perguntou por que não tinham sido coletados. Não tinham porque a regra 10 só deixa coletar perfil confirmado por uma pessoa.

- `data/config/atores.json`: confirmados X `FDisenso` e Facebook `fundaciondisenso` (Fundación Disenso), Instagram `santi_abascal` (Santiago Abascal) e X `ecader` (Eduardo Cader), com a frase do responsável como fonte. Continua candidato: Facebook `SantiagoAbascalConde`.
- `data/config/coleta.json`: teto da carga do Instagram de US$ 0,20 para US$ 0,35 e do Facebook de US$ 4,50 para US$ 5,80, só para estes perfis, com a frase de autorização. No X não houve aumento: cabe no teto de US$ 2,00 já autorizado.

**O que foi realmente executado.** `python -m unittest discover -s tests` → 53 testes, OK. As cargas estão na entrada seguinte.

## E1.12 — 15/11/2026 · Contagem do que irá para a área do pesquisador

**O que foi realmente executado.** Run 43754059281 (`area-pesquisador.yml`, modo seco: conta e não envia; não usa o Supabase), com o repositório privado: 207.500 textos — 7.357 publicações e 200.143 comentários do YouTube com texto (dos 200.166 guardados, 23 não têm texto). Por ator: Vox 5.852 publicações e 199.541 comentários; Abascal 836 e 0; Foro Madrid 317 e 58; Fundación Disenso 197 e 544; Martín Frías 155 e 0.

**Pendente.** O mesmo da entrada E1.11: nada foi aplicado nem enviado ao Supabase.

## E1.11 — 15/11/2026 · Área do pesquisador (Supabase) trazida do ODI Atlas; banco ainda não criado

**O que mudou e por quê.** O responsável pediu "uma área interna como do projeto original" e informou o projeto Supabase `zlrzraqngiszsgoedlfv`.

- Copiados sem alteração do ODI Atlas: `supabase/migrations/` (6 arquivos), `supabase/functions/odi-area-config/`, `supabase/tests/00_simula_supabase.sql`, `assets/odi-concordancia.js`, `data/config/livro_codigos_validacao.json`. A busca do banco usa configuração neutra de idioma (`simple` + `unaccent`), então serve para textos em espanhol.
- `area-pesquisador.html`: cópia do original com três trocas (título, endereço do projeto Supabase, link de volta para `index.html`).
- `scripts/carregar_area_pesquisador.py`: adaptado. Aqui cada "caso" é um ator monitorado. Entram as publicações do acervo público e os comentários do YouTube do repositório privado. Comentário nunca leva autor nem canal do autor. Triagem automática de ofensa e ódio fica vazia: os modelos do original são para português.
- `data/casos/indice.json`: título de cada "caso" (ator), para a página.
- `.github/workflows/area-pesquisador.yml`: carga manual; chave de serviço pelo secret `SUPABASE_SERVICE_ROLE_KEY_ESP`.
- `AGENTS.md`, regra 11: comentários também podem ir, sem autor, para a área interna com login.
- Não trazido: a função `odi-chat` do original (usa chave do Gemini, com custo).

**O que foi realmente executado.** `python -m unittest discover -s tests` → 53 testes, OK (carga, RLS em todas as tabelas públicas das migrações, página sem chave). `python scripts/carregar_area_pesquisador.py --seco` no acervo público: 7.357 publicações com texto (Vox 5.852, Abascal 836, Foro Madrid 317, Disenso 197, Martín Frías 155). A contagem com os comentários do privado está na entrada seguinte.

**⛔ Não feito: nada foi aplicado no Supabase.** O conector do Supabase desta sessão não enxerga o projeto `zlrzraqngiszsgoedlfv` (só três projetos de outra organização), então as migrações e a função não foram aplicadas e a página ainda não funciona. Falta: aplicar as 6 migrações em ordem; publicar `odi-area-config` sem exigência de JWT; configurar o endereço da página no login; convidar os pesquisadores e incluí-los em `public.pesquisadores`; cadastrar o secret; rodar a carga.

## E1.10 — 15/11/2026 · Telas no modelo do ODI Atlas: O que dizem, Quem acompanha, Comentários, Trends e Anúncios

**O que mudou e por quê.** O responsável pediu as páginas "conforme era no ODI Atlas original" (O que dizem, Comentários, Quem acompanha, Trends), mantendo as telas já feitas. `index.html` passou de 6 para 11 cadernos; os 6 anteriores continuam iguais.

- **O que dizem** (modelo do caderno "O que as campanhas dizem"): por rede, universo e amostra de cada perfil, números por ator, filtro por tema e por tipo de mensagem, linha do tempo semana a semana em bolhas, tabela de temas, nuvens e hashtags por ator, publicações de maior audiência, método. Lê `data/<rede>/conteudo.json`.
- **Quem acompanha**: seguidores por perfil e por rede, com data e fonte da leitura. Lê `data/site/resumo.json`.
- **Comentários**: universo × lido do YouTube por ator, série mensal, e o universo de Instagram, X e Facebook pelos contadores. Lê `data/youtube/comentarios/cobertura.json`.
- **Anúncios · Meta e Google**: contexto do TTPA, buscas da Biblioteca da Meta (lidos, nome exato, classificados como políticos e retirados, meses e destinos), Central de Transparência do Google. Lê `data/meta/anuncios.json` e `data/google_ads/transparencia.json`. O custo da coleta não aparece; o valor investido pelos anunciantes é dado da Biblioteca.
- **Buscas · Google Trends**: tela criada com ⛔ não coletado.

**Marcado como ⛔ nas próprias telas (não feito):** livro de códigos de populismo e CHD de Reinert; rede de coocorrência; análises dos comentários (termos, códigos de intolerância, sentimento, CHD, redes de conversação); coletor do Google Trends; série diária de seguidores; comentários de Instagram, X e Facebook.

**O que foi realmente executado.** `node --check` no script da página; navegador sem interface (Chrome via Playwright) abrindo a página em servidor local com os dados reais do repositório: os 11 cadernos abrem sem erro de console; "O que dizem" desenha as quatro redes e responde ao filtro de tema; "Comentários" mostra 199.735 / 200.166 / 32.240 / 1.216, iguais aos de `cobertura.json`; "Anúncios" mostra 496/302/36, 342/0/52, 2/1/2 e 502/0/4, iguais aos de `anuncios.json`. `python -m unittest discover -s tests` → 47 testes, OK.

**Pendente.** Conferir a página publicada (GitHub Pages); área interna do pesquisador (Supabase), como no projeto original.

## E1.9 — 15/11/2026 · Comentários do YouTube lidos por inteiro; agregados dos anúncios regravados

**O que foi realmente executado.**

- Run 43751204452 (`anuncios.yml`, recuperação, sem custo): agregados da Meta regravados com as colunas novas. Classificados como políticos pela Meta e retirados: "VOX España" 52, "Santiago Abascal" 36, "Foro Madrid" 4, "Fundación Disenso" 2 (94 no total). Evidência: `data/meta/anuncios.json`, `data/meta/anuncios_apify.csv`.
- Run 43751313353 (`gratuitas.yml`, opção `comentarios`): primeira leitura completa dos comentários do YouTube, 3.245 chamadas à API oficial (teto 7.000), sem custo. Universo informado pela plataforma (soma do contador dos vídeos do acervo): 199.735. Lidos: 200.166 comentários e respostas, com a paginação dos 1.216 vídeos levada até o fim.
  - Vox: universo 199.133 em 1.115 vídeos; lidos 199.564, dos quais 32.128 respostas; 41.023 autores distintos.
  - Fundación Disenso: universo 544 em 74 vídeos com contador; lidos 544; 11 dos 85 vídeos têm comentários desativados.
  - Foro Madrid: universo 58 em 16 vídeos; lidos 58.
  - O lido passa do universo no Vox porque o contador é o da coleta dos vídeos e os comentários continuaram chegando.
  - Texto e autor estão só no `odi-secret-esp` (`youtube/comentarios/comentarios.csv.gz` e `estado.json`); no público, `data/youtube/comentarios/cobertura.json`, só contagens.

**Pendente.** Análise dos comentários (termos, temas, CHD, rede de respostas) e tela "Comentários"; tela "Anúncios"; busca de anúncios pela página; comentários de Instagram, Facebook e X, que dependem de teto de gasto ainda não autorizado.

## E1.8 — 15/11/2026 · Repositório privado gravando; bruto recuperado; o que os anúncios da Meta são de fato

**O que foi realmente executado.**

- Run 43749706245 (`recuperar-bruto.yml`): o `ODI_INTERNO_TOKEN` clonou e gravou no `odi-secret-esp`. Bruto de 36 execuções já pagas copiado sem nova execução: 12.451 itens (X 9 execuções, 3.460; Instagram 17, 6.985; Facebook 4, 658; anúncios da Meta 4, 1.342; fichas de perfil 2 execuções, 6). Evidência: anotações do run e `data/bruto_privado.json`.
- Run 43750391336 (`anuncios.yml`, recuperação): Google respondeu às buscas (5 respostas de busca, 6 de anúncios): "VOX" trouxe 10 sugestões, nenhuma da Espanha; os outros 4 termos, nenhuma; os 3 sites oficiais não têm anúncio. Ausência lida, não falha. Limite: a busca por nome só vê as 10 sugestões da Central. Na Meta, a recuperação por comparação do pedido não achou as execuções (4 × `LookupError`).
- Commit f9b6eb7 (sem entrada própria neste arquivo, registrado aqui): a recuperação da Meta passou a ler as execuções guardadas no privado, identificando a busca pelo campo `input` dos itens.
- Run 43750795404 (`anuncios.yml`, recuperação): 1.342 anúncios relidos sem custo, incluindo os 496 de "Santiago Abascal" que não tinham sido baixados. O custo daquela execução entrou no manifesto.
- `python -m unittest discover -s tests` → 47 testes, OK.

**O que os dados mostram** (`data/meta/anuncios_apify.csv` e leitura do bruto privado em 15/11/2026; cópia temporária apagada depois).

- Nome como frase exata: "Santiago Abascal" 302 de 496 lidos (33 páginas anunciantes; início entre 26/04 e 12/11/2026; 193 em julho); "Fundación Disenso" 1 de 2; "VOX España" 0 de 342; "Foro Madrid" 0 de 502. Nenhuma busca bateu no limite de 600.
- Dos 302 de Abascal: 267 são anúncios de catálogo (texto em modelo), 11 repetem a chamada "pierde el control tras la revelación financiera"; destinos exibidos: amazon.com 95, elmundo.es 101, e domínios que imitam o El Mundo (elmundo-es.com 21, elmund0.es 15, elmnd0.es 6), capitalfirst.world 16, webflux.cc 10. 300 dos 302 já estavam inativos. Nenhum é de página dos atores monitorados. Leitura: padrão compatível com anúncio de golpe financeiro que usa o nome do político e imita veículo de imprensa; falta conferência humana da amostra no privado.
- 94 anúncios foram classificados pela Meta como políticos (`categories=POLITICAL`) e todos constam como retirados (`gated_type=TAKEN_DOWN`); 92 começaram dentro do período do estudo, isto é, depois de 06/10/2025. Páginas com mais casos: VOX Gandía 18, Killit NV 10, PSOE Vega Baja 9. Moedas: EUR 57, USD 26, NOK 5, CHF 3, GBP 3.
- Correção de rótulo: o campo `reach_estimate` é o tamanho estimado do público-alvo (ex.: ">1M"), não alcance. A coluna pública passou de `alcance_*` para `publico_estimado_*`. Só os anúncios classificados como políticos trazem gasto e público estimado.

**O que mudou no código.** `collect_meta_anuncios_apify.py`: colunas `politico`, `retirado`, `moeda`, `destino`; agregados por consulta (classificados como políticos, retirados, gasto por moeda sem somar moedas diferentes, destinos e meses dos anúncios com frase exata).

**Pendente.** Rodar a recuperação de novo para regravar os agregados com as colunas novas; primeira leitura dos comentários do YouTube; busca de anúncios pela página (identificadores das páginas oficiais); telas "Anúncios" e "Comentários".

## E1.7 — 15/11/2026 · Resultado dos anúncios, recuperação do bruto sem custo e comentários do YouTube

**Resultado real dos anúncios (run 43748071016, workflow `anuncios.yml`).**

- Meta, Biblioteca de Anúncios, Espanha, todos os tipos de anúncio, desde 16/02/2026: 846 anúncios lidos em 3 das 4 buscas. "Foro Madrid" 502 (154 páginas anunciantes), "VOX España" 342 (106 páginas), "Fundación Disenso" 2, "Santiago Abascal" ⛔ (`IncompleteRead`: a execução foi feita, o resultado não foi baixado e o custo dela não ficou registrado). Nenhuma busca bateu no limite de 600. Custo registrado no manifesto `data/meta/manifesto-2026-11-*.json` (teto US$ 0,40).
- A busca da Biblioteca casa palavras soltas: em "Foro Madrid" nenhuma das 154 páginas tem o nome de um ator; em "VOX España" a maior anunciante é uma marca de móveis. O número bruto não mede anúncios dos atores. Por isso o coletor passou a marcar, sem publicar texto, quais anúncios trazem o nome como frase exata (`frase_exata` em `data/meta/anuncios_apify.csv`).
- Google, Central de Transparência, Espanha: 0 anunciantes e 0 anúncios nas 5 buscas e nos 3 sites oficiais. O coletor marcava ⛔ porque não distinguia "li e não há" de "não li"; agora registra se a Central respondeu (`diagnostico` em `data/google_ads/transparencia.json`).
- O texto dos anúncios desta execução não foi guardado: o repositório privado ainda recusava a gravação.

**O que mudou e por quê.**

- `scripts/recuperar_bruto.py` + `recuperar-bruto.yml`: copia para o repositório privado o resultado das execuções da Apify já feitas e pagas. Não inicia execução, não gasta, não mexe no acervo nem no registro de gasto. No público, só contagens (`data/bruto_privado.json`). Motivo: o responsável avisou em 15/11/2026 que o `ODI_INTERNO_TOKEN` agora grava no `odi-secret-esp`; as cargas foram feitas antes disso.
- `scripts/collect_meta_anuncios_apify.py`: opção `--recuperar` (relê execuções já pagas, nunca roda de novo; custo de execução já registrada não é somado outra vez); custo de execução feita e não baixada passa a entrar no manifesto; marca de frase exata.
- `scripts/collect_google_transparencia.py`: diagnóstico de resposta da Central; nomes sugeridos pela busca vão só ao privado.
- `scripts/collect_comentarios_youtube.py` + `data/config/comentarios.json` + passo em `gratuitas.yml`: comentários e respostas dos vídeos do acervo pela API oficial, sem custo, no método do ODI Atlas. Texto e autor só no privado; no público, `data/youtube/comentarios/cobertura.json` com universo × lido.
- `AGENTS.md`, regra 11: comentários de terceiros passam a ser lidos, só com o privado disponível e só para o privado, a pedido do responsável (página "Comentários").
- Gravação no privado tolera repositório ainda vazio (envia antes de puxar).

**Universo de comentários, pelo contador de cada publicação já lida** (`data/<rede>/posts.csv.gz`): Instagram 762.478, X 478.141 (respostas), Facebook 306.326, YouTube 199.735. Ressalvas: no Instagram, 1.424 das 1.928 publicações do Vox trazem contador e as da Disenso e de Martín Frías não trazem; no Facebook, a amostra do Vox é parcial (603 publicações).

**O que foi realmente executado.** `python -m unittest discover -s tests` → 46 testes, OK. As execuções reais deste passo (verificação do token, bruto, comentários) estão na entrada seguinte.

**Pendente.** Teto de gasto para comentários de Instagram, Facebook e X; busca de anúncios por página (precisa do identificador das páginas); telas "Anúncios" e "Comentários" na página.

## E1.6 — 15/11/2026 · Anúncios do Google e da Meta, como no ODI Atlas

**O que mudou e por quê.** O responsável pediu: "quero que puxe os anúncios do meta e google também como fizemos no odi atlas".

- `scripts/collect_google_transparencia.py`: cópia do coletor do ODI Atlas (Central de Transparência de Anúncios, navegador sem login, sem custo), com a região vinda da configuração (Espanha) e nome curto de anunciante casando só por inteiro.
- `scripts/collect_meta_anuncios_apify.py` e `scripts/meta_agregar.py`: cópia do coletor e da agregação do ODI Atlas (Biblioteca de Anúncios da Meta via ator jmlp/meta-ad-library-scraper), com país, tipo de anúncio e segredo vindos da configuração.
- `data/config/google_transparencia.json` e `data/config/meta_anuncios.json`: buscas pelos nomes dos atores e pelos três sites oficiais; teto da Meta US$ 0,40 para uma leitura do período, com a frase de autorização.
- `.github/workflows/anuncios.yml`: execução manual.

**Contexto que muda a leitura.** O Google deixou de veicular anúncios políticos na União Europeia em 22/09/2025 e a Meta em 06/10/2025, por causa do regulamento europeu de publicidade política (TTPA). No período do estudo (desde 16/02/2026) não existe, nas duas plataformas, anúncio político declarado na Espanha. Por isso a busca na Meta é em todos os anúncios (`ad_type=all`), e ausência de resultado é o esperado, não falha de coleta.

**O que foi realmente executado.** `python -m unittest discover -s tests` → 39 testes, OK. As execuções reais deste passo estão na entrada seguinte, depois de rodarem.

## E1.5 — 15/11/2026 · "O que dizem": método do ODI Atlas portado (dados; a tela ainda não)

**O que mudou e por quê.** O responsável pediu as páginas do ODI Atlas original (O que as campanhas dizem → "O que dizem", Comentários, Quem acompanha, Trends), com a mesma metodologia, e perguntou se o modelo de `ODI_Atlas_v15_MVP.html` já tinha sido importado. **Não tinha:** até aqui só a identidade visual. Este passo porta a primeira parte, a dos dados de "O que dizem".

- `scripts/texto.py`: regras de texto de `build_conteudo.py` do Atlas (normalização, dicionário aberto por regras com prefixo `*`, descarte de trechos repetidos em 10+ publicações do mesmo perfil, nuvem por nº de publicações, hashtags), com palavras vazias do espanhol.
- `data/config/temas.json`: dicionário de temas em espanhol, **versão v0, rascunho a validar** (13 temas, lista de adversários, expressões de pedido de voto, fases). As datas da campanha oficial foram calculadas pela regra geral e estão marcadas "a conferir" no calendário da Junta Electoral Central.
- `scripts/build_o_que_dizem.py`: gera `data/<rede>/conteudo.json` no desenho do Atlas, com um bloco por ator (temas, visualizações por tema, taxa de interação mediana, cita adversário, pede voto, nuvem, hashtags, por mês e por fase, lista de publicações). Entrou nos dois workflows.

**O que foi realmente executado.**
- `python -m unittest discover -s tests` → 37 testes, OK.
- `python scripts/build_o_que_dizem.py` no acervo real (local, 15/11/2026). Publicações com pelo menos um tema do dicionário v0: Instagram 73,8% de 2.143; X 68,2% de 3.372; Facebook 73,4% de 644; YouTube 55,4% de 1.216. Os arquivos gerados localmente não foram commitados; o workflow os gera.

**O que NÃO foi feito (⛔).** A tela "O que dizem" (linha do tempo em bolhas, nuvens, listas); o livro de códigos de populismo em espanhol; a CHD de Reinert; as redes de coocorrência e de menções no modelo dos casos; e as páginas Comentários, Quem acompanha e Trends. O dicionário v0 não passou por codificação humana nem teste de concordância: os percentuais por tema ainda não servem para análise.

## E1.4 — 15/11/2026 · Cargas de X, Instagram e Facebook; correção da regra de cobertura

**Errata (importante).** O manifesto da carga do Facebook (`data/facebook/manifesto-20261115T…`, run 43744078867) grava a página `vox.espana` como "completa". **Está errado.** O ator devolveu 603 posts, todos de 18/10 a 15/11/2026, e parou sozinho, longe da data inicial (16/02/2026). A regra antiga só olhava se o número de itens tinha batido no limite pedido (804) ou no limite conhecido do ator (700). Correção:
- `comum.classificar`: cobertura "completa" só sem nenhum sinal de corte; leitura com 500 itens ou mais cuja publicação mais antiga fica a mais de 30 dias da data inicial é "parcial ⛔";
- `coleta.json`: limite do ator do Facebook passa a 600, com o run como evidência;
- `build_acervo.py`: a página recalcula a cobertura pela regra atual em vez de confiar no texto gravado no manifesto. O manifesto original não foi alterado.
- A estimativa dada ao responsável antes da carga (cerca de 7 posts por dia na página do Vox) veio de um teste com 7 posts e estava errada: o ritmo medido é de cerca de 21 por dia (603 em 29 dias).

**O que foi realmente executado (15/11/2026), com universo e amostra.**
- **X, carga:** run 43740489231, custo US$ 0,5058. Lidos no período, do mais recente até a data inicial: `vox_es` 2.220, `Santi_ABASCAL` 836, `Foro_MAD` 177, `jm_frias` 139 (3.372 com os do teste). A publicação mais antiga lida é de 16/02/2026 em três perfis e de 19/02/2026 em `jm_frias`. Universo que o X informa (toda a vida da conta, com reposts): 108.587, 50.476, 2.963 e 19.881. O X não informa total por período; a leitura é a busca do próprio X (posts, respostas e citações, sem reposts).
- **Instagram, carga:** run 43741114895, custo registrado US$ 0,031: `fundaciondisenso` 113 no período (182 itens, 69 de outra conta), `foromadrid` 83 (124 itens, 41 de outra conta), `jmartinfrias` 19 (82 itens, 63 de outra conta). `vox_es` foi executado na Apify, mas o download do resultado caiu (IncompleteRead): custo desse perfil não registrado (até US$ 0,19 pelo teto da execução). Releitura do `vox_es`: run 43745182745, custo US$ 0,169: 1.928 no período (2.906 itens, 978 de outra conta), de 16/02 a 15/11/2026; nenhuma execução anterior pôde ser reaproveitada. Itens "de outra conta" são publicações em colaboração cujo dono é outro perfil; ficaram fora do acervo.
- **Universo por perfil (sonda):** run 43742217822. Instagram informa o total de publicações da conta: `vox_es` 11.493, `fundaciondisenso` 1.143, `foromadrid` 578, `jmartinfrias` 289. O Facebook informa só seguidores. Os 5 candidatos não foram sondados (sem repositório privado). No X, a sonda só devolveu `Foro_MAD`; o universo dos outros três vem da própria carga.
- **Facebook, carga:** run 43744078867, custo US$ 4,489 (teto 4,50). `ForoMadridOficial`: 41 no período, de 16/02 a 07/09/2026, cobertura completa. `vox.espana`: 603 posts de 18/10 a 15/11/2026, **parcial ⛔** (ver errata).
- `python -m unittest discover -s tests` → 33 testes, OK.

**Gasto registrado nos manifestos até aqui:** US$ 5,28 (Facebook 4,56; X 0,52; Instagram 0,20) de um saldo informado de US$ 10. Pode haver até US$ 0,19 a mais da execução do Instagram cujo resultado não foi baixado.

**O que NÃO foi feito (⛔).** Bruto da Apify não guardado (o `ODI_INTERNO_TOKEN` segue sem acesso ao `odi-secret-esp`). Facebook do Vox antes de 18/10/2026. Diário. 5 perfis candidatos. Páginas pedidas pelo responsável em 15/11 (O que dizem, Comentários, Quem acompanha, Trends) e redes e IRaMuTeQ no modelo dos casos do ODI Atlas.

## E1.3 — 15/11/2026 · Data final, carga de X e Instagram, universo por perfil

**O que mudou e por quê.** O responsável respondeu: "final 30/01/2027", "pode rodar" a carga de Instagram e X com o saldo atual, e pediu o tamanho do universo para responder à orientação e prever custos.

- `projeto.json`: `periodo.ate = 2027-01-30`.
- `coleta.json`: carga liberada no Instagram (teto US$ 0,20) e no X (teto US$ 2,00); uma leitura do universo por perfil (sonda, teto US$ 0,20). Facebook e diário seguem em zero.
- `build_acervo.py`: o universo lido pela sonda entra na página onde ainda não há foto diária de perfis.
- `coleta.json` (2º commit do dia): saldo informado de US$ 10; carga do Facebook liberada pelo responsável com teto de US$ 4,50, ciente de que o bruto não será guardado enquanto o `ODI_INTERNO_TOKEN` estiver sem acesso.
- `comum.py`: o manifesto registra quantos itens devolvidos eram de outra conta ou foram descartados.
- `apify.py` e `comum.py` (3º commit do dia): o resultado da Apify é baixado em páginas, com nova tentativa; execução feita cujo resultado não foi baixado entra no manifesto com o seu custo; `--recuperar --perfis=...` reaproveita execução já paga das últimas 48 h em vez de pagar de novo. Motivo: na carga do Instagram (run 43741114895) o perfil `vox_es` foi executado na Apify e o download do resultado caiu (IncompleteRead); o manifesto daquele run registra custo zero para esse perfil, o que subestima o gasto real.

**O que foi realmente executado.** `python -m unittest discover -s tests` → 29 testes, OK. As execuções pagas deste passo estão registradas na entrada seguinte, depois de rodarem.

## E1.2 — 15/11/2026 · YouTube com dados reais; teste da Apify autorizado

**O que mudou e por quê.** O responsável cadastrou segredos e informou o orçamento: "feito apify tem 5 dolares mais vamos contratar um pacote de 20 dolares pra coleta completa ok".

- `data/config/coleta.json`: frase de autorização gravada nas três redes; liberado só o modo **teste** (Instagram US$ 0,10, X US$ 0,10, Facebook US$ 0,30; soma US$ 0,50 de um saldo informado de US$ 5). Carga e diário continuam em zero.
- Workflows: o aviso do repositório privado agora distingue "segredo não cadastrado" de "sem acesso".

**O que foi realmente executado.**
- `python -m unittest discover -s tests` → 29 testes, OK.
- **YouTube, com dados reais:** workflow *Coletas sem custo*, run 43737756941 (15/11/2026, 16h51 UTC), sucesso. Evidência em `data/youtube/manifesto_latest.json`, `data/youtube/posts.csv.gz` e `data/perfis/youtube_latest.csv`. Universo (total de vídeos que o YouTube informa por canal, toda a vida do canal) e amostra (vídeos lidos no período, lista de envios lida até a data inicial):
  - Vox (`voxespana`): universo 6.172; lidos no período 1.115; cobertura completa.
  - Fundación Disenso (`@fundaciondisenso`): universo 339; lidos 85; cobertura completa.
  - Foro Madrid: universo 87; lidos 16; cobertura completa.
  - Acervo: 1.216 vídeos. Corpus IRaMuTeQ gerado com 1.216 textos (título e descrição).
- Sites, mesmo run: sem publicações novas (Foro Madrid 20 de 20 e 1 de 1; Disenso 129 pelo RSS; Vox ⛔ HTTP 403).

- **Teste da Apify, com dados reais:** workflow *Coleta*, modo teste, run 43737932481 (15/11/2026), sucesso. Custo total cobrado: US$ 0,088 (Instagram 0,004; X 0,012; Facebook 0,072), dentro do teto de US$ 0,50. Evidência nos `manifesto_latest.json` de `data/instagram`, `data/x` e `data/facebook`. O teste lê as publicações mais recentes de cada perfil e não mede cobertura:
  - X (20 pedidos por perfil, 20 lidos em cada): `Foro_MAD`, `vox_es`, `Santi_ABASCAL`, `jm_frias`. Preço conferido: US$ 0,00015 por post. Universo que o X informa (toda a vida da conta, com reposts): 2.963, 108.587, 50.476 e 19.881 publicações.
  - Instagram (10 pedidos por perfil, 10 itens em cada): do próprio perfil e no período, `vox_es` 10, `fundaciondisenso` 8, `jmartinfrias` 3, `foromadrid` 2. Os demais itens devolvidos pertencem a outra conta (publicações em colaboração) e ficaram fora pelo filtro de dono. Visualizações dos reels lidas na 2ª leitura.
  - Facebook (10 pedidos por página, 7 lidos em cada): `vox.espana` e `ForoMadridOficial`. Preço conferido: US$ 0,005 por post + US$ 0,001 por execução.
  - Acervo depois do teste: 1.333 publicações (1.216 do YouTube, 80 do X, 23 do Instagram, 14 do Facebook).

**O que NÃO foi executado (⛔).** Nenhuma carga paga: as redes têm só a amostra do teste. O repositório privado não gravou nada: no run 43737932481 o `ODI_INTERNO_TOKEN` estava cadastrado, mas sem acesso de escrita ao `odi-secret-esp`; o bruto do teste não foi guardado e não há texto integral dos sites.

**Pendências.** `ODI_INTERNO_TOKEN` com acesso antes de qualquer carga paga (sem ele o bruto da Apify se perde); data final do período; pacote de US$ 20; tetos de carga e diário; decidir se publicações do Instagram em colaboração (dono é outra conta) entram no acervo; 5 perfis candidatos a conferir.

## E1.1 — 14/11/2026 · Perfis corrigidos, YouTube e notícias dos sites oficiais

**O que mudou e por quê.** O responsável mandou endereços (Instagram de Jorge Martín Frías e da Fundación Disenso, canal de YouTube da Disenso, os sites foromadrid.org, voxespana.es e fundaciondisenso.org/articulos/, a Junta Electoral Central) e pediu as frentes do ODI Atlas (YouTube, Trends, checagens, buscas nas redes, TikTok, grupos, Telegram) e um quadro com as notícias publicadas pelos sites.

- **Perfis** (`data/config/atores.json`): 13 de 24 endereços confirmados (eram 5 de 18). O site oficial foromadrid.org lista X `Foro_MAD`, Instagram `foromadrid`, Facebook `ForoMadridOficial` e o canal de YouTube; os candidatos anteriores de Foro Madrid (`ForoMadrid_`, `foromadrid_`) estavam **errados**, nunca foram coletados e foram substituídos (registro em `correcoes`). Confirmados pelo responsável: Instagram `jmartinfrias` e `fundaciondisenso`, YouTube `@fundaciondisenso`.
- **YouTube** (`scripts/collect_youtube.py`): API oficial, sem custo, segredo `YOUTUBE_API_KEY`. Universo = total de vídeos que o YouTube informa por canal; a lista de envios é lida até a data inicial.
- **Sites** (`scripts/collect_sites.py`, `data/config/sites.json`): notícias e artigos de fundaciondisenso.org, foromadrid.org e voxespana.es pela API pública do WordPress (com o total que o próprio site informa, no cabeçalho X-WP-Total) e, se ela não responder, pelo RSS paginado. Respeita robots.txt. No público, só metadados (título, datas, tipo, seções, autor, endereço); resumo e texto integral só no repositório privado.
- **Automação**: `gratuitas.yml` (sites e YouTube, todo dia; YouTube é pulado sem o segredo). Saúde: séries sem custo.
- **Testes**: os testes dos coletores passaram a usar uma configuração fixa (`tests/fixtures/config`), para não quebrarem quando um perfil real é confirmado ou corrigido.
- **Contexto** (`projeto.json`): eleições gerais na Espanha em 29/11/2026, lido no site da Junta Electoral Central em 14/11/2026.

- **Página**: caderno 05 "Sites oficiais" (o que cada site informa, o que foi lido e a lista de publicações com filtros); YouTube nas tabelas e no gráfico.

**O que foi realmente executado.**
- `python -m unittest discover -s tests` → 29 testes, OK (local, 14/11/2026).
- **Sites, com dados reais:** workflow *Coletas sem custo*, run 43641402671 (14/11/2026, 21h10 UTC), sucesso. Evidência em `data/sites/manifesto-20261114T211050Z.json` e `data/sites/artigos.csv.gz`:
  - foromadrid.org, pela API do WordPress: 21 publicações no período (posts: 20 lidos de 20 que o site informa no período, total do site 185; encuentros-reg: 1 de 1, total 5). Cobertura completa.
  - fundaciondisenso.org: o robots.txt não permite `/wp-json`, então a leitura foi pelo RSS: 129 publicações de 16/02/2026 a 12/11/2026, lidas até a data inicial. Universo ⛔ desconhecido (o RSS não informa total). A seção "Artículos" é uma categoria dos posts (66 das 129).
  - voxespana.es: ⛔ HTTP 403 ao servidor do GitHub (API e RSS). Nada lido; sem tentativa de contorno.
  - Sem `ODI_INTERNO_TOKEN`, só os metadados públicos foram lidos (nenhum texto integral).
- Página aberta no Chrome sem interface nos seis cadernos, sem erro de console, com os 150 registros reais dos sites.

**O que NÃO foi executado (⛔).** YouTube com dados reais (falta o segredo `YOUTUBE_API_KEY`; só respostas simuladas). Nenhuma chamada à Apify.

**Pendências.** As da E1.0 (data final, tetos, segredos), mais: segredo `YOUTUBE_API_KEY`; endereços de Telegram, TikTok e grupos; termos para Trends, checagens e buscas. 5 candidatos a conferir (Disenso no X e no Facebook; Abascal no Instagram e no Facebook; Cader no X) e 6 não localizados.

## E1.0 — 14/11/2026 · Estrutura do Atlas (sem coleta)

**O que mudou.** Criação do repositório a partir da arquitetura do ODI Atlas (`WandersonH/odi-atlas`, commit `3f318c7`), a pedido do responsável em 14/11/2026: novo Atlas com as contas de Instagram, X e Facebook de Foro Madrid, Vox, Fundación Disenso, Santiago Abascal, Jorge Martín Frías e Eduardo Cader, desde 16/02/2026.

- **Configuração** (`data/config/`): projeto e período; 6 atores × 3 redes = 18 endereços, cada um com situação e fonte; atores Apify, preços (herdados do ODI Atlas, com data) e tetos, todos em zero.
- **Coletores** (`scripts/`): `comum.py` (núcleo) e `collect_instagram_posts.py`, `collect_x_posts.py`, `collect_facebook_posts.py`, portados dos coletores do ODI Atlas, com os modos teste, carga e diário; `collect_perfis.py` (seguidores, universo e sonda de conferência).
- **Agregadores**: `build_acervo.py` (página), `exportar_corpus.py` (IRaMuTeQ), `build_rede_mencoes.py` (GEXF e CSV para Gephi e NodeXL), `build_saude_coleta.py`.
- **Automação** (`.github/workflows/`): `coleta.yml` (agendado e manual), `saude-coleta.yml`, `testes.yml`; `commit_push.sh` e `resolver_conflitos.py` portados.
- **Página** (`index.html`): cinco cadernos, com a folha de estilo do ODI Atlas.

**Diferenças deliberadas em relação ao ODI Atlas.**
- Nenhuma consulta de saldo ou de limites da conta Apify; uma conta dedicada (`APIFY_TOKEN_ESP`); uma leitura por vez, cada uma com o que sobra do teto.
- Um único workflow de coleta (as três redes em sequência), para não haver duas execuções gravando os mesmos arquivos.
- Execução em que todos os perfis falham termina ⛔ (no ODI Atlas, os manifestos de Facebook e X de 12 a 14/11/2026 dizem "ok" com HTTP 401 em todos os perfis).
- Publicação sem data fica fora do acervo e é contada no manifesto (`sem_data`).
- Sem autorização de gasto, o diário agendado não coleta e não falha; a saúde mostra a série como "inativa".

**O que foi realmente executado.**
- `python -m unittest discover -s tests` → 24 testes, OK (Python 3.13.18, local, 14/11/2026). Os coletores foram exercitados só com respostas simuladas.
- `python scripts/build_acervo.py` e `python scripts/build_saude_coleta.py` na raiz → `data/site/resumo.json`, `data/site/indice.json` e `data/saude_coleta.json` do estado atual (0 publicações; 5 de 18 perfis confirmados; 4 séries inativas).
- Workflow *Testes* no GitHub: run 43639027359, sucesso (push do commit `942de21`, 14/11/2026, 20h43 UTC).
- Página aberta no Chrome sem interface nos cinco cadernos, sem erro de console, em dois estados: o deste repositório (vazio) e uma pasta temporária com publicações sintéticas, que não foi commitada.

**O que NÃO foi executado (⛔).**
- Nenhuma chamada à Apify. Nenhuma publicação real foi lida. Os pedidos enviados a cada ator são os do ODI Atlas, mas não foram testados contra a Apify neste repositório.
- Os workflows *Coleta* e *Saúde da coleta* ainda não rodaram no GitHub (só o de testes).
- Os preços não foram reconferidos na loja da Apify (são os de 17 e 18/10/2026).

**Pendências, todas do responsável.**
1. Data final do período: o pedido traz "30/20/2027". `periodo.ate` está nulo.
2. Perfis: 8 candidatos a conferir (Foro Madrid no X e no Instagram; Fundación Disenso nas três redes; Abascal no Instagram e no Facebook; Cader no X) e 5 não localizados (Foro Madrid no Facebook; Martín Frías e Cader no Instagram e no Facebook). Os sites foromadrid.org e fundaciondisenso.org não puderam ser abertos pela ferramenta de leitura em 14/11/2026.
3. Teto de gasto e frase de autorização por rede em `data/config/coleta.json`; segredos `APIFY_TOKEN_ESP` e `ODI_INTERNO_TOKEN` no GitHub.
4. Ativar o GitHub Pages (branch `main`, raiz) para a página ficar no ar.
5. Crédito de fomento no rodapé, se este Atlas estiver sob a mesma bolsa do ODI Atlas.

**Evidência.** `tests/` (24 testes), `data/site/resumo.json`, `data/saude_coleta.json`.
