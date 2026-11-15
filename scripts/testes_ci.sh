#!/usr/bin/env bash
# Roda os testes e, se falharem, publica cada falha como anotação do GitHub (legível sem acesso ao log completo).
# A rede de coocorrência usa networkx (mesma versão do ODI Atlas); o resto, só a biblioteca padrão.
pip install -q networkx==3.6.1 numpy==2.3.4 scipy > /dev/null 2>&1 || echo "::warning title=Testes::networkx não instalado"
out=$(python -m unittest discover -s tests 2>&1); rc=$?
echo "$out" | tail -n 3
if [ $rc -ne 0 ]; then
  echo "$out" | grep -E "^(ERROR|FAIL):|Error:|AssertionError" | head -n 15 | while IFS= read -r l; do echo "::error title=Testes::$(echo "$l" | cut -c1-300)"; done
fi
exit $rc
