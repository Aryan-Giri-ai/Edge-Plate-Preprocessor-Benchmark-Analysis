"""Native trace integrity, pixel agreement, benchmark and Streamlit checks."""
from pathlib import Path
import copy,io,json,sys,tempfile,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from image_ops import sample
from pipeline_core import run_demo,benchmark,audit_trace,event_rows_at,events,export_result
checks=[];rng=np.random.default_rng(260826)
for h,w in [(3,3),(13,17),(90,160)]:
    images=[rng.integers(0,256,(h,w,3),dtype=np.uint8) for _ in range(3)]
    result=run_demo(images,18,3,80,2)
    assert result["runs"]["B"]["audit"]["thread_id_count"]==1
    assert result["runs"]["D"]["audit"]["thread_id_count"]==4
    for threshold in [0,1020]:run_demo(images,9,3,threshold,5)
checks.append("native B/D capture equality and Python reference at small/border sizes and thresholds 0/80/1020")
full=rng.integers(0,256,(1080,1920,3),dtype=np.uint8)
large=run_demo([full],8,2,80,5)
checks.append("1920x1080 full-byte equality for grayscale, binary Sobel and closed captures")
images=[np.roll(sample(),i*7,axis=1).copy() for i in range(3)]
result=run_demo(images,48,3,80,5)
run=result["runs"]["D"]
assert run["audit"]["peak_wall_interval_overlap"]>1
clock=next(e["begin"]+(e["end"]-e["begin"])/2 for e in events(run) if e["worker"]==3)
status=event_rows_at(run,clock)
assert any(r["worker"]==3 and r["active_frame"] is not None for r in status)
changed=copy.deepcopy(run);changed["frames"][1]["slot_id"]="-1"
try:audit_trace(changed,"D",48)
except ValueError:pass
else:raise AssertionError("Invalid slot accepted")
changed=copy.deepcopy(run);changed["frames"][0]["gray_begin_ms"]="-10"
try:audit_trace(changed,"D",48)
except ValueError:pass
else:raise AssertionError("Invalid stage time accepted")
try:run_demo([images[0],images[0][:-1]],12,2)
except ValueError:pass
else:raise AssertionError("Mixed dimensions accepted")
checks.append("measured pipeline overlap, replay-time service lookup and rejection of damaged traces/mixed resolutions")
b=benchmark(images,24,3,3)
assert len(b["runs"])==6 and b["capture"]==0 and b["paired_ratio"]>0
with zipfile.ZipFile(io.BytesIO(export_result(images,result,["one","two","three"],b))) as z:
    assert z.testzip() is None
    assert "benchmark.json" in z.namelist() and "D/workers.csv" in z.namelist()
checks.append("randomized capture-free paired benchmark with six retained raw runs and downloadable evidence")
from streamlit.testing.v1 import AppTest
at=AppTest.from_file(str(ROOT/"app.py"),default_timeout=60).run()
assert not at.exception and "completed" not in at.session_state
at.number_input[0].set_value(24)
at.button[0].click().run()
assert not at.exception
assert at.session_state["completed"][2]["runs"]["D"]["audit"]["thread_id_count"]==4
at.button[2].click().run()
assert not at.exception and at.session_state["event_index"]==1
at.radio[1].set_value("B — Sequential").run()
assert not at.exception
assert at.session_state["completed"][2]["runs"]["B"]["audit"]["thread_id_count"]==1
# Captured frame control changes the view without new native execution.
digest=at.session_state["completed"][2]["replay_sha256"]
at.slider[-1].set_value(1).run()
assert not at.exception and at.session_state["completed"][2]["replay_sha256"]==digest
at.number_input[2].set_value(24)
at.number_input[3].set_value(3)
at.number_input[4].set_value(3)
at.button[4].click().run()
assert not at.exception and at.session_state["bench"]["capture"]==0
checks.append("Streamlit Run gating, actual four-worker result, event stepping, B/D trace switch, captured-frame selection and benchmark form")
at.radio[0].set_value("Local dataset").run()
at.text_input[0].set_value("/missing/review3").run()
at.button[0].click().run()
assert not at.exception and len(at.error)>0
checks.append("invalid local path displays an actionable error")
report={"passed":True,"host":"Linux","checks":checks,
        "limits":["Native Windows execution untested here","No hardware CPU-core trace","New tests use generated inputs, not UFPR source images"]}
(ROOT/"tests/VALIDATION.json").write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))

