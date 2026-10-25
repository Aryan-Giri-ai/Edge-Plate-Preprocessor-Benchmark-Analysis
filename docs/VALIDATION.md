# Release validation — 26 October 2026

This public source was prepared from the saved Review 3 archive with SHA-256 3bd57f86980f8fc37649fc1e04827e6917243e1db140a3301ed21546b916bd47.

## Completed here on Linux

- Original archive SHA-256/CRC checks and all 1,728 packaged-file hash checks.
- Audit of its historical 20-run / 12,000-frame six-image study.
- Fresh public-source Bash build.
- Existing independent kernel suite across all seven configurations and both source/legacy profiles.
- Bounded-queue pressure, malformed input, paced/RAM/file replay and worker-failure shutdown checks.
- Independent grayscale, binary Sobel and closing capture checks for A/B/D.
- Native-size mixed-resolution preparation: coverage, hashes, replay byte counts and full-byte B/D captures.
- Fresh 640×360 synthetic A/B/D demo: one sequential thread, four pipeline workers, matching capture bytes and valid slot order.
- Separate generic baseline and pipeline launchers.
- Three-block primary synthetic pilot and two-block seven-configuration synthetic smoke study; both audits passed. These runs were deliberately short workflow checks, not publication performance evidence.
- Local Markdown link and hardware-specific wording checks.

The numerical kernels, shared runtime and native entry points are unchanged from the source archive. The public package changes documentation, launchers, preparation utilities, evidence pointers and repository packaging.

## Limits

Native Windows/MSYS2 execution has not been performed here. The CMake output paths were adjusted for the family-directory layout, but CMake/CTest were unavailable in this environment; the verified build path is scripts/build.sh. The GitHub Actions workflow is supplied, not claimed to have run remotely. Browser launch availability depends on the user's desktop; generated HTML/image paths are checked locally.

The original large review archive contains saved traffic-derived visual evidence. The public ZIP contains source, documentation and text-only historical aggregate examples. It does not contain datasets, private Drive links, native binaries, local measurements or generated captures.

