#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p native/bin
suffix=""
links=(-pthread)
if [[ -n "${MSYSTEM:-}" ]]; then
  [[ "$MSYSTEM" == "UCRT64" ]] || { echo "Use MSYS2 UCRT64"; exit 1; }
  suffix=".exe"; links+=(-lpsapi)
fi
"${CXX:-g++}" -std=c++20 -O3 -DNDEBUG -pthread \
  -Iengine/shared/include engine/shared/src/app.cpp \
  engine/baseline/src/main.cpp "${links[@]}" -o "native/bin/edge_seq$suffix"
echo "Built native/bin/edge_seq$suffix"

