# CHANGELOG

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
