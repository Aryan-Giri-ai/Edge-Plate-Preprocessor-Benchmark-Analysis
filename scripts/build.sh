#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
compiler="${CXX:-g++}"
target="${1:-all}"
case "$target" in all|baseline|pipeline) ;; *) echo "Target must be all, baseline or pipeline" >&2; exit 1;; esac
if [[ -n "${MSYSTEM:-}" && "$MSYSTEM" != "UCRT64" ]]; then echo "Open MSYS2 UCRT64." >&2; exit 1; fi
suffix=""
links=(-pthread)
if [[ "${MSYSTEM:-}" == "UCRT64" ]]; then
 suffix=".exe"; links+=(-lpsapi)
 if [[ "$($compiler -dumpmachine)" != "x86_64-w64-mingw32" ]]; then echo "Use UCRT64 GCC." >&2; exit 1; fi
fi
mkdir -p build baseline/build pipeline/build
flags=(-std=c++20 -O3 -DNDEBUG -Wall -Wextra -Wpedantic -pthread -Ishared/include)
"$compiler" "${flags[@]}" -c shared/src/app.cpp -o build/app.o
if [[ "$target" == "all" || "$target" == "baseline" ]]; then
 "$compiler" "${flags[@]}" baseline/src/main.cpp build/app.o "${links[@]}" -o "baseline/build/edge_seq$suffix"
fi
if [[ "$target" == "all" || "$target" == "pipeline" ]]; then
 "$compiler" "${flags[@]}" pipeline/src/main.cpp build/app.o "${links[@]}" -o "pipeline/build/edge_pipeline$suffix"
fi
"$compiler" "${flags[@]}" tests/kernels.cpp -o "build/kernel_tests$suffix"
{
 "$compiler" --version
 "$compiler" -dumpmachine
 printf 'flags: %s\n' "${flags[*]}"
 printf 'links: %s\n' "${links[*]}"
 printf 'MSYSTEM: %s\n' "${MSYSTEM:-Linux}"
} > build/build_info.txt
for family in baseline pipeline; do
 if [[ "$target" == "all" || "$target" == "$family" ]]; then cp build/build_info.txt "$family/build/build_info.txt"; fi
done
echo "Built $target. Executables are in baseline/build/ and pipeline/build/."
