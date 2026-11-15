# CHANGELOG

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
