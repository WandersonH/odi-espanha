#!/usr/bin/env bash
# Roda a coleta pedida, uma rede por vez, e publica cada linha da saída como anotação do GitHub.
# uso: scripts/coletar.sh <modo: teste|carga|diario|sonda> <rede: todas|instagram|x|facebook|perfis>
# No diário, série sem teto autorizado é pulada com aviso (não é falha). Sai com 1 se alguma coleta executada falhou.
set -u
modo="$1"; rede="${2:-todas}"; falhou=0
um() {  # um <título> <comando...>
  titulo="$1"; shift
  rc=0; "$@" > _saida.txt 2>&1 || rc=$?
  while IFS= read -r l; do echo "::notice title=${titulo}::$(echo "$l" | cut -c1-900)"; done < _saida.txt
  rm -f _saida.txt
  [ $rc -eq 0 ] || { echo "::error title=${titulo}::terminou com código $rc"; falhou=1; }
}
if [ "$modo" = "sonda" ]; then
  um "Perfis (sonda)" python scripts/collect_perfis.py --sonda
  exit $falhou
fi
case "$modo" in teste|carga|diario) ;; *) echo "::error title=Coleta::modo desconhecido: $modo"; exit 1;; esac
for r in instagram x facebook; do
  [ "$rede" = "todas" ] || [ "$rede" = "$r" ] || continue
  if [ "$modo" = "diario" ] && ! python scripts/autorizacao.py "$r" diario; then
    echo "::notice title=${r}::diário sem teto autorizado em data/config/coleta.json — pulado"; continue
  fi
  extra=()
  [ -n "${PERFIS:-}" ] && extra+=("--perfis=${PERFIS}")
  [ "${RECUPERAR:-false}" = "true" ] && extra+=("--recuperar")
  um "$r ($modo)" python "scripts/collect_${r}_posts.py" "--$modo" "${extra[@]}"
done
if [ "$modo" = "diario" ] && { [ "$rede" = "todas" ] || [ "$rede" = "perfis" ]; }; then
  if python scripts/autorizacao.py perfis diario; then
    um "Perfis (diário)" python scripts/collect_perfis.py --diario
  else
    echo "::notice title=perfis::diário sem teto autorizado em data/config/coleta.json — pulado"
  fi
fi
exit $falhou
