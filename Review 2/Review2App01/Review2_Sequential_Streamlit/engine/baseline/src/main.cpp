#include "app.hpp"
// A (--allocation dynamic) and B (--allocation pool) share the source profile.
// Paper: Chen et al., 2024, DOI 10.1016/j.procs.2024.09.149, Sec. 4.4.
// Patent: US6553131B1, Fig. 1 block 16; preprocessing subset only.
// Exact scope and project-selected constants: docs/SOURCE_ALIGNMENT.md.
int main(int argc, char** argv) { return edge::run(argc, argv, false); }
