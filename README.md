# ODI Espanha

Atlas das publicações públicas de **Foro Madrid, Vox, Fundación Disenso, Santiago Abascal, Jorge Martín Frías e Eduardo Cader** no **Instagram, no X e no Facebook**, a partir de 16/02/2026. Construído sobre a arquitetura do [ODI Atlas](https://github.com/WandersonH/odi-atlas), do Observatório de Desinformação e Intolerância Digital (ODI) · PPGCOM/UNIP.

> **Estado em 14/11/2026: estrutura pronta, ⛔ nenhuma publicação coletada.** Faltam três decisões do responsável (abaixo). O registro do que foi feito e testado está no `CHANGELOG.md`.

## O que falta para a primeira coleta

1. **Data final do período.** O pedido traz "30/20/2027" (mês inexistente). Enquanto `data/config/projeto.json → periodo.ate` for nulo, a carga lê de 16/02/2026 até o dia da execução e o diário segue rodando.
2. **Perfis.** 5 dos 18 endereços estão confirmados com fonte (Vox nas três redes; Abascal e Martín Frías no X). 8 são candidatos a conferir e 5 não foram localizados (`data/config/atores.json`). Para incluir um perfil: abrir o endereço, confirmar que é o oficial, gravar `"confirmado": true`, a `fonte` e `conferido_em`.
3. **Gasto.** Gravar em `data/config/coleta.json` o teto de cada rede e a frase de autorização, e cadastrar no GitHub os segredos `APIFY_TOKEN_ESP` (conta Apify dedicada a este Atlas) e `ODI_INTERNO_TOKEN` (acesso de escrita ao repositório privado `odi-secret-esp`).

Preços herdados do ODI Atlas (lidos na loja da Apify em 17 e 18/10/2026; o manifesto de cada execução registra o custo real):

| Rede | Ator | Preço por 1.000 publicações | Limite conhecido |
|---|---|---|---|
| Instagram | esdrasdw/instagram-content-scraper | US$ 0,05 (+ uma 2ª leitura dos reels, para as visualizações) | — |
| X | xquik/x-tweet-scraper | US$ 0,15 | sem reposts |
| Facebook | apify/facebook-posts-scraper | US$ 5,00 + US$ 0,001 por execução | para perto de 700 a 1.000 posts por página; não aceita data final |

## Como rodar

Pelo GitHub: *Actions → Coleta → Run workflow*, escolhendo o modo.

| Modo | O que faz |
|---|---|
| `sonda` | Lê nome, selo e seguidores dos perfis (inclusive candidatos) para apoiar a conferência. Ficha de candidato só no repositório privado. |
| `teste` | Poucas publicações por perfil confirmado: confere ator, preço real e perfil. |
| `carga` | Todo o período, do post mais recente para trás, até o teto. |
| `diario` | Publicações dos últimos 2 dias. É o que o agendamento roda (02h23 de Brasília), só nas séries com teto autorizado. |
| `so-analises` | Sem coleta e sem custo: regera a página, o corpus e a rede. |

Local (sem custo): `python -m unittest discover -s tests -v` e `python scripts/build_acervo.py`.

## Como ler um resultado

- **Universo e amostra.** O universo é o total de publicações que a plataforma informa para o perfil (toda a vida da conta). Nenhuma das três redes informa o total dentro do período; o Facebook não informa total nenhum. O que a plataforma não informa aparece como ⛔ desconhecido.
- **Cobertura do período.** "Completa" = a leitura parou pela data inicial. "Parcial ⛔" = parou no limite pedido ou no limite do ator; pode haver publicações mais antigas não lidas.
- **"Coleta em dia" não é "coleta completa".** A saúde diz se chegou dado novo dentro de 36 horas; a cobertura de cada perfil está no caderno 01 da página.
- **Rede de marcações.** É a rede de saída (quem os perfis citam). Citar não é apoiar; uma comunidade da rede não é, sozinha, uma "bolha".

## Onde está cada coisa

| Caminho | Conteúdo |
|---|---|
| `data/config/` | Projeto e período, atores e perfis (com fonte), atores Apify, preços e tetos, séries da saúde |
| `scripts/comum.py` | Núcleo dos coletores: perfis confirmados, teto, período, universo e amostra, manifesto |
| `scripts/collect_{instagram,x,facebook}_posts.py` | Coletores de posts (portas dos coletores do ODI Atlas) |
| `scripts/collect_perfis.py` | Seguidores e universo por perfil; sonda de conferência |
| `scripts/build_acervo.py` | Agregados da página (`data/site/`) |
| `scripts/exportar_corpus.py` | Corpus IRaMuTeQ (`data/corpus/`) |
| `scripts/build_rede_mencoes.py` | Rede de marcações em GEXF e CSV para Gephi e NodeXL (`data/redes/`) |
| `scripts/build_saude_coleta.py` | Saúde da coleta (`data/saude_coleta.json`) |
| `data/<rede>/posts.csv.gz` | Acervo público: uma linha por publicação, mesmas colunas nas três redes |
| `data/<rede>/manifesto-*.json` | Uma ficha por execução: pedido, lido, cobertura, erro, custo |
| `index.html` | Página (identidade visual do ODI Atlas) |

O bruto devolvido pela Apify fica em `WandersonH/odi-secret-esp` (privado).

## Licenças

- Código: MIT (`LICENSE`).
- Dados derivados produzidos aqui: CC BY 4.0.
- As publicações pertencem aos seus autores; aqui estão reproduzidas para pesquisa, com o endereço original de cada uma.
