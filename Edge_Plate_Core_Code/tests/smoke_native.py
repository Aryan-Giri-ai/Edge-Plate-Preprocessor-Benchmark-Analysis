"""Build-output check with generated RGB input; not a performance benchmark."""
import csv
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

def rows(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))

def main():
    width, height, count, frames, capture = 24, 16, 3, 36, 3
    suffix = ".exe" if os.name == "nt" else ""
    with tempfile.TemporaryDirectory(prefix="edge_core_check_") as temp:
        base = Path(temp)
        source = base / "generated.epraw"
        with source.open("wb") as handle:
            handle.write(b"EPRAW01\n" + struct.pack("<III", width, height, count))
            for image_id in range(count):
                handle.write(bytes((x * 13 + y * 17 + c * 61 + image_id * 29) % 256
                                   for y in range(height) for x in range(width) for c in range(3)))
        fingerprints = {}
        for mode, expected_workers in [("seq", 1), ("pipeline", 4)]:
            executable = ROOT / "native/bin" / ("edge_" + mode + suffix)
            if not executable.is_file():
                raise SystemExit("Build first: bash native/build.sh")
            out = base / mode
            subprocess.run([str(executable), "--input", str(source), "--out", str(out),
                            "--frames", str(frames), "--capture", str(capture),
                            "--profile", "source", "--edge-threshold", "80",
                            "--allocation", "pool", "--traversal", "row",
                            "--slots", "34", "--queue", "5"], check=True)
            assert (out / "SUCCESS").is_file(), "missing completion marker"
            frame_rows = rows(out / "frames.csv")
            worker_rows = rows(out / "workers.csv")
            assert len(frame_rows) == frames
            assert len({r["thread_id"] for r in worker_rows}) == expected_workers
            previous_slot_end = {}
            for i, row in enumerate(frame_rows):
                assert int(row["frame_id"]) == i
                assert int(row["source_index"]) == i % count
                previous_end = None
                for stage in ["fetch", "gray", "sobel", "output"]:
                    begin, end = float(row[stage + "_begin_ms"]), float(row[stage + "_end_ms"])
                    assert begin <= end
                    if previous_end is not None:
                        assert previous_end <= begin + 1e-7
                    previous_end = end
                slot = int(row["slot_id"])
                if slot in previous_slot_end:
                    assert previous_slot_end[slot] <= float(row["fetch_begin_ms"]) + 1e-7
                previous_slot_end[slot] = previous_end
            for row in rows(out / "queues.csv"):
                assert float(row["high_watermark"]) <= int(row["capacity"])
            fingerprints[mode] = [(r["source_index"], r["sum"], r["weighted_sum"]) for r in frame_rows]
            print(f"PASS {mode}: {frames} frames, {expected_workers} worker identities, ordered stages and safe slot reuse")
        assert fingerprints["seq"] == fingerprints["pipeline"]
        for filename in ["captured_gray.raw", "captured_binary.raw", "captured_edges.raw"]:
            assert (base / "seq" / filename).read_bytes() == (base / "pipeline" / filename).read_bytes()
        print("PASS captured gray, binary and closed-edge planes match byte for byte")
        print("Generated input checks software behavior; it is not a UFPR accuracy or throughput result.")

if __name__ == "__main__":
    main()
