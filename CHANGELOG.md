# CHANGELOG

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
