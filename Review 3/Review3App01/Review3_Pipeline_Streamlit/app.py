from pathlib import Path
import io
import numpy as np
import pandas as pd
import altair as alt
import streamlit as st
from image_ops import sample,load_image
from pipeline_core import ready,run_demo,benchmark,events,event_rows_at,captured_images,export_result,NAMES

st.set_page_config(page_title="Review 3 | Native Pipeline",layout="wide")
st.title("Pipelined image preprocessing")
st.caption("Review 3 • actual C++ workers • measured frame order • Sobel and morphological closing")
st.write("Run the sequential baseline and four-stage pipeline on identical frames, then inspect the recorded execution.")
if not ready():
    st.warning("Build both native engines first. This app does not simulate thread execution.")
    st.code('bash native/build.sh',language="bash")
source=st.radio("Image source",["Generated sequence","Upload images","Local dataset"],horizontal=True)
uploads=[];selected=[]
if source=="Upload images":
    uploads=st.file_uploader("Select 1 to 12 images with the same original dimensions",
         type=["png","jpg","jpeg","bmp","ppm"],accept_multiple_files=True)
elif source=="Local dataset":
    folder=st.text_input("Dataset image folder",r"E:\NEW DOWNLOADS\VIT Downloads\Other Downloads\Assignments")
    if st.button("Find images"):
        try:
            p=Path(folder)
            if not p.is_dir():raise ValueError("Choose an existing extracted image folder.")
            paths=sorted(str(x) for x in p.rglob("*") if x.is_file() and x.suffix.lower() in {".png",".jpg",".jpeg",".bmp",".ppm"})
            if len(paths)>10000:raise ValueError("Choose a smaller dataset subfolder.")
            st.session_state["catalog"]=paths;st.session_state["catalog_root"]=folder
            if not paths:st.warning("No images found.")
        except (ValueError,OSError) as e:st.error(str(e))
    if st.session_state.get("catalog_root")==folder and st.session_state.get("catalog"):
        paths=st.session_state["catalog"]
        selected=st.multiselect("Select source images",paths,default=paths[:min(6,len(paths))],max_selections=12)
with st.form("demo"):
    count=st.number_input("Replayed frames",min_value=2,max_value=600,value=120,step=1)
    cap=st.number_input("Captured frames",min_value=1,max_value=6,value=3,step=1)
    threshold=st.slider("Binary edge threshold",0,1020,80)
    queue=st.selectbox("Pipeline queue capacity",[2,5,10],index=1)
    run=st.form_submit_button("Run baseline and native pipeline",type="primary",disabled=not ready())
if run:
    try:
        if source=="Generated sequence":
            base=sample();images=[np.roll(base,i*7,axis=1).copy() for i in range(6)]
            names=[f"Generated pattern {i} (synthetic)" for i in range(6)]
        elif source=="Upload images":
            images=[load_image(io.BytesIO(f.getvalue())) for f in uploads];names=[f.name for f in uploads]
        else:images=[load_image(p) for p in selected];names=selected
        with st.spinner("Executing actual B and D runs and checking output equality…"):
            result=run_demo(images,int(count),int(cap),threshold,queue)
        st.session_state["completed"]=(images,names,result)
        st.session_state.pop("bench",None);st.session_state["event_index"]=0
    except Exception as e:
        st.session_state.pop("completed",None);st.error(str(e))
if "completed" not in st.session_state:
    st.info("Choose sources and Run. Each frame follows W1 → W2 → W3 → W4; different frames may overlap.")
else:
    images,names,result=st.session_state["completed"]
    st.success(result["correctness"])
    st.caption(f"Completed run: {len(images)} distinct sources; {result['frames']} replayed frames; "
               f"threshold {result['threshold']}; queue {result['queue']}; 34 pipeline slots. "
               "Changing controls does not change this record until Run is submitted.")
    st.subheader("Actual thread execution")
    mode=st.radio("Trace to inspect",["D — Pipeline","B — Sequential"],horizontal=True)
    key=mode[0];trace=result["runs"][key]
    st.write("Native thread identities:",trace["audit"]["thread_id_count"],
             " | Peak overlapping wall intervals:",trace["audit"]["peak_wall_interval_overlap"])
    st.dataframe(trace["workers"],hide_index=True,width="stretch")
    all_events=events(trace)
    first=st.slider("First frame in timeline",0,result["frames"]-1,0)
    window=[e for e in all_events if first<=e["frame"]<first+12]
    chart=(alt.Chart(pd.DataFrame(window)).mark_bar(size=22).encode(
        x=alt.X("begin:Q",title="Measured run time (ms)",scale=alt.Scale(zero=False)),
        x2="end:Q",y=alt.Y("stage:N",sort=NAMES,title=""),
        color=alt.Color("frame:N",title="Frame"),tooltip=["frame","source","slot","stage","begin","end"]))
    clocks_for_rule=sorted({e[t] for e in all_events for t in ["begin","end"]})
    prior_index=st.session_state.get("event_index",0) if st.session_state.get("event_mode")==key else 0
    replay_clock=clocks_for_rule[min(prior_index,len(clocks_for_rule)-1)]
    if min(e["begin"] for e in window)<=replay_clock<=max(e["end"] for e in window):
        rule=alt.Chart(pd.DataFrame({"clock":[replay_clock]})).mark_rule(color="#d62728",size=2).encode(x="clock:Q")
        chart=chart+rule
    st.altair_chart(chart.properties(height=240),width="stretch")
    st.caption("Bars use actual native timestamps. B's four stage rows share one thread identity. D has four workers. "
               "Wall overlap can include preemption and is not a CPU-core trace.")
    st.subheader("Step through recorded events")
    clocks=sorted({e[t] for e in all_events for t in ["begin","end"]})
    if st.session_state.get("event_mode")!=key:
        st.session_state["event_index"]=0;st.session_state["event_mode"]=key
    c1,c2,c3=st.columns(3)
    if c1.button("Previous event"):
        st.session_state["event_index"]=max(0,st.session_state.get("event_index",0)-1)
    if c2.button("Next event"):
        st.session_state["event_index"]=min(len(clocks)-1,st.session_state.get("event_index",0)+1)
    if c3.button("Reset replay"):st.session_state["event_index"]=0
    position=st.slider("Recorded event index",0,len(clocks)-1,key="event_index")
    clock=clocks[position];active=event_rows_at(trace,clock)
    st.write(f"Recorded time: {clock:.3f} ms")
    st.dataframe([{"stage":NAMES[r["worker"]-1],
                   "frame in recorded service":str(r["active_frame"]) if r["active_frame"] is not None else "No service interval"}
                  for r in active],hide_index=True,width="stretch")
    st.caption("This is playback of completed execution. It does not launch threads while you move the slider.")
    with st.expander("Consecutive stage events"):
        st.dataframe(sorted(all_events,key=lambda e:(e["begin"],e["worker"])),hide_index=True,width="stretch")
    st.subheader("Actual captured Sobel results")
    idx=st.slider("Captured frame",0,result["capture"]-1,0) if result["capture"]>1 else 0
    st.write("Source:",names[idx%len(names)])
    maps=captured_images(images,result,idx)
    labels=[("input","Original RGB"),("grayscale","Integer grayscale"),("contrast","Captured contrast grayscale"),
            ("sobel_preview","Vertical Sobel response"),("binary","Captured binary Sobel"),
            ("closed","Captured pipeline closed edges"),("baseline","Captured sequential closed edges"),
            ("difference","B–D difference"),("closing_change","Pixels changed by closing")]
    for offset in range(0,len(labels),3):
        cols=st.columns(3)
        for col,(k,label) in zip(cols,labels[offset:offset+3]):col.image(maps[k],caption=label,width="stretch")
    st.caption("Contrast grayscale, binary Sobel and closed maps are actual C++ captures. Raw grayscale and the fixed "
               "0–1020 response preview are Python diagnostic views. Black B–D difference means equal captured pixels, not recognition accuracy.")
    st.subheader("This frame through consecutive workers")
    row=result["runs"]["D"]["frames"][idx]
    identities={int(w["worker"]):w["thread_id"] for w in result["runs"]["D"]["workers"]}
    st.dataframe([{"stage":NAMES[i],"thread ID":identities[i+1],"slot":row["slot_id"],
                   "begin ms":float(row[stage+"_begin_ms"]),"end ms":float(row[stage+"_end_ms"])}
                  for i,stage in enumerate(["fetch","gray","sobel","output"])],hide_index=True,width="stretch")
    st.caption("This captured frame follows its stages in order. The pipeline timeline shows other frames overlapping that route.")
    st.subheader("Demonstration measurements")
    st.dataframe([{"mode":k,"FPS with capture":r["summary"]["fps"],
        "P95 ms":r["summary"]["latency_p95_ms"],"Peak MiB":r["summary"]["peak_process_rss_mib"]}
        for k,r in result["runs"].items()],hide_index=True,width="stretch")
    st.caption("Capture-enabled, short demonstration runs are not the primary performance experiment.")
    with st.expander("Optional capture-free paired benchmark"):
        st.write("Uses the images and numerical settings of the completed demo above. Preselect a sufficient frame count from a pilot.")
        with st.form("benchmark"):
            bf=st.number_input("Timed frames per process",min_value=2,max_value=10000,value=600)
            br=st.number_input("Paired blocks",min_value=3,max_value=10,value=3)
            bw=st.number_input("Warmup frames",min_value=0,max_value=1000,value=60)
            bench_run=st.form_submit_button("Run capture-free comparison",disabled=not ready())
        if bench_run:
            try:
                progress=st.progress(0.0)
                st.session_state["bench"]=benchmark(images,int(bf),int(br),int(bw),
                    result["threshold"],result["queue"],lambda value:progress.progress(value))
            except Exception as e:st.session_state.pop("bench",None);st.error(str(e))
        if "bench" in st.session_state:
            b=st.session_state["bench"]
            st.write(f"Paired geometric D/B ratio: {b['paired_ratio']:.3f}; "
                     f"95% bootstrap interval: {b['ci95'][0]:.3f}–{b['ci95'][1]:.3f}.")
            st.dataframe([{"block":r["block"],"mode":r["mode"],"FPS":r["summary"]["fps"],
                          "P95 ms":r["summary"]["latency_p95_ms"],"peak MiB":r["summary"]["peak_process_rss_mib"]}
                          for r in b["runs"]],hide_index=True,width="stretch")
            if b["repeats"]<10 or b["minimum_run_seconds"]<5:
                st.warning("Exploratory pilot: use ten paired blocks and sufficiently long runs for the planned study.")
            st.caption("This interval covers run-level variation in this experiment, not dataset or hardware generalization.")
    st.download_button("Download captures and execution records",
          export_result(images,result,names,st.session_state.get("bench")),"review3_execution.zip","application/zip")
    st.info("W3 computes the complete Sobel/threshold/closing stage for each frame. The workers overlap different frames. "
            "No model training, plate detector or OCR is implemented.")

