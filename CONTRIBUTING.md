# Contributing

Use docs/SETUP.md. Keep numerical kernels shared between programs. Document algorithm changes as separate treatments.

Before proposing a change:
1. Build with bash scripts/build.sh.
2. Run python scripts/check.py and python tests/check_capture.py.
3. Run the small synthetic demo in README.md.
4. For preparation changes, run python tests/check_prepare_groups.py.
5. For performance claims, retain repeated paired measurements, manifests, build information and machine context.

Describe the problem, change, validation and limitations in the issue or pull request. Do not upload datasets, private paths, credentials or generated captures.

