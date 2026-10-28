#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p native/bin
suffix=""
links=(-pthread)
if [[ -n "${MSYSTEM:-}" ]]; then
 [[ "$MSYSTEM" == "UCRT64" ]] || { echo "Open MSYS2 UCRT64"; exit 1; }
 suffix=".exe"; links+=(-lpsapi)
fi
compiler="${CXX:-g++}"
flags=(-std=c++20 -O3 -DNDEBUG -Wall -Wextra -Wpedantic -pthread -Iengine/shared/include)
"$compiler" "${flags[@]}" -c engine/shared/src/app.cpp -o native/bin/app.o
"$compiler" "${flags[@]}" engine/baseline/src/main.cpp native/bin/app.o "${links[@]}" -o "native/bin/edge_seq$suffix"
"$compiler" "${flags[@]}" engine/pipeline/src/main.cpp native/bin/app.o "${links[@]}" -o "native/bin/edge_pipeline$suffix"
echo "Built sequential and four-worker pipeline engines"

