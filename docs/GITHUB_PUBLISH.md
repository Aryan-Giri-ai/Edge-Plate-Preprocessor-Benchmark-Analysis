# Repository root and publishing

## Which directory to push

Push the contents of the extracted edge-plate-preprocessor folder as one repository. README.md, CMakeLists.txt, baseline/, pipeline/, shared/, scripts/ and docs/ belong at the root.

Do not initialize Git in just baseline/ or pipeline/: they depend on shared/ and common scripts. Use this clean source folder rather than uploading the complete academic archive, which contains dataset-derived images and generated evidence.

## Public framework

| Element | Included |
| --- | --- |
| Entry points | baseline/src/main.cpp and pipeline/src/main.cpp |
| Shared implementation | shared/include/ and shared/src/ |
| Build definitions | scripts/build.sh, family build.sh and CMakeLists.txt |
| Dependencies | requirements.txt and docs/SETUP.md |
| Checks | tests/ and scripts/check.py |
| Inputs | Synthetic generator and generic image/group preparation |
| Evaluation | Benchmarks, analysis, audits and demo generation |
| Provenance | Source mapping, license, third-party boundaries and citation metadata |
| Examples | Labeled historical aggregate tables |
| Local workspace | Ignored data/, results/, evidence/ and family build/results |
| Contributions | CONTRIBUTING.md and Linux CI workflow |

The application has no particular laptop configuration requirement. Publish dataset acquisition instructions rather than UFPR images or annotations.

## First push

Create an empty GitHub repository named edge-plate-preprocessor. Leave GitHub's README, license and .gitignore initialization boxes unselected: those files are already supplied.

Authenticate your terminal using an SSH key or an approved HTTPS credential method. Replace the identity and URL placeholders below:

~~~bash
cd "/path/to/edge-plate-preprocessor"
git init -b main
git config user.name "YOUR NAME"
git config user.email "YOUR VERIFIED OR NOREPLY EMAIL"
git add .
git status --short
git diff --cached --stat
~~~

Check that data payloads, generated runs and binaries are absent.

~~~bash
git commit -m "Add sequential and pipelined preprocessing with reproducible evaluation"
git remote add origin https://github.com/YOUR_USERNAME/edge-plate-preprocessor.git
git push -u origin main
~~~

GitHub account passwords are not used for HTTPS Git authentication; use your configured credential method.

If the folder is already a repository, inspect git status and git remote -v first. Do not overwrite origin or force-push to solve a mismatch. These instructions assume an empty remote.

## Later updates

~~~bash
git status
git add README.md docs scripts shared baseline/src pipeline/src tests config
git diff --cached --stat
git commit -m "Describe the actual change"
git push
~~~

New results are ignored by default. To deliberately share a benchmark, curate text-only records under examples/ with scope, machine context and provenance. Keep original raw evidence separately.

The landing page should show README.md immediately. Add the real repository URL to CITATION.cff and the reports after it exists. This package does not preclaim a GitHub URL.

Official reference: https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github

