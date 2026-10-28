from pathlib import Path
from datetime import datetime,timezone
import io
import streamlit as st
from processing import sample,load_image,process,png_bytes,export_zip,native_path

st.set_page_config(page_title="Review 2 | Sequential Preprocessing",layout="wide")
st.title("Sequential image preprocessing")
st.caption("Review 2 • grayscale → contrast → vertical Sobel → threshold → closing")
st.write("Process one image through the stages in order. Inspect each map and download the actual result.")
source=st.radio("Image source",["Generated pattern","Upload image","Local dataset"],horizontal=True)
selected=None;uploaded=None
if source=="Local dataset":
    folder=st.text_input("Dataset image folder",r"E:\NEW DOWNLOADS\VIT Downloads\Other Downloads\Assignments")
    if st.button("Find images"):
        try:
            root=Path(folder)
            if not root.is_dir():raise ValueError("Choose an existing local dataset folder.")
            paths=sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in {".png",".jpg",".jpeg",".bmp",".ppm"})
            if len(paths)>10000:raise ValueError("Choose a smaller folder containing at most 10,000 images.")
            st.session_state["catalog"]=[str(p) for p in paths]
            st.session_state["catalog_root"]=folder
            if not paths:st.warning("No supported images found.")
        except (OSError,ValueError) as e:st.error(str(e))
    if st.session_state.get("catalog") and st.session_state.get("catalog_root")==folder:
        selected=st.selectbox("Select one image",st.session_state["catalog"])
elif source=="Upload image":
    uploaded=st.file_uploader("PNG, JPEG, BMP or PPM",type=["png","jpg","jpeg","bmp","ppm"])

with st.form("processing"):
    engine=st.selectbox("Execution engine",["Python sequential","Native C++ sequential"],
                        index=1 if native_path().exists() else 0)
    threshold=st.slider("Binary edge threshold",0,1020,80,
                        help="80 is the documented baseline. Other thresholds are exploratory settings.")
    run=st.form_submit_button("Run sequential preprocessing",type="primary")
if engine=="Python sequential":
    st.caption("Standalone Python equivalent. Operations execute in order; no separate stage workers are created.")
else:
    st.caption("Runs the original pooled C++ sequential baseline and checks its captured maps against Python.")
if run:
    try:
        with st.spinner("Processing in sequence…"):
            if source=="Generated pattern":rgb=sample();name="Generated pattern (synthetic)"
            elif source=="Upload image" and uploaded is not None:
                rgb=load_image(io.BytesIO(uploaded.getvalue()));name=uploaded.name
            elif source=="Local dataset" and selected:rgb=load_image(selected);name=selected
            else:raise ValueError("Upload or select an image first.")
            arrays,meta=process(rgb,threshold,engine)
            meta.update(source_name=name,created_utc=datetime.now(timezone.utc).isoformat())
            st.session_state["result"]=(arrays,meta)
    except Exception as e:
        st.session_state.pop("result",None);st.error("Processing failed: "+str(e))

if "result" not in st.session_state:
    st.info("Choose an input and press Run sequential preprocessing.")
else:
    arrays,meta=st.session_state["result"]
    st.subheader("Completed run")
    st.write(f"Source: {meta['source_name']}")
    st.caption(f"{meta['width']} × {meta['height']} • {meta['engine']} • threshold {meta['threshold']}. "
               "These outputs belong to this completed run. Submit again after changing controls.")
    labels=[("input","1  Original RGB"),("grayscale","2  Integer grayscale"),
            ("contrast","3  Fixed contrast"),("gradient_preview","4  Vertical Sobel response"),
            ("binary","5  Thresholded edges"),("closed","6  Final closed edges"),
            ("closing_change","Pixels changed by closing")]
    for start in range(0,len(labels),3):
        cols=st.columns(3)
        for col,(key,label) in zip(cols,labels[start:start+3]):
            col.image(arrays[key],caption=label,width="stretch")
    st.caption("Sobel preview: fixed 0–1020 to 0–255 scale. Thresholding uses the original response. "
               "Grayscale before contrast and the response preview are Python diagnostic views; native mode verifies the three native capture planes.")
    st.subheader("Sequential stage record")
    if "native_summary" in meta:
        st.success(meta["parity"])
        st.dataframe(meta["native_frames"],width="stretch")
        st.dataframe(meta["native_workers"],width="stretch")
        st.write("Native processing interval:",round(meta["native_summary"]["elapsed_s"]*1000,3),"ms")
    else:
        rows=[dict(stage=e["stage"],begin_ms=round(e["begin_ms"],3),end_ms=round(e["end_ms"],3),
                   duration_ms=round(e["end_ms"]-e["begin_ms"],3)) for e in meta["python_stage_events"]]
        st.dataframe(rows,hide_index=True,width="stretch")
        st.write("Python transform interval:",round(meta["python_transform_ms"],3),"ms")
    st.caption("Single-image demonstration timings are not baseline/pipeline benchmark results. GUI rendering, "
               "optional parity computation and process startup have different timing boundaries.")
    a,b=st.columns(2)
    a.download_button("Download final edge PNG",png_bytes(arrays["closed"]),"closed_edges.png","image/png")
    b.download_button("Download images and run record",export_zip(arrays,meta),"sequential_run.zip","application/zip")
    with st.expander("Algorithm and Review 2 scope"):
        st.markdown("""**Grayscale:** (299R + 587G + 114B + 500) // 1000.  
**Contrast:** clamp((5Y + 2) // 4 − 32, 0, 255).  
**Edges:** absolute Gx with the 3×3 Sobel kernel.  
**Binary map:** 255 when |Gx| reaches the threshold, otherwise zero.  
**Closing:** 3×3 dilation then erosion, with the documented zero border.  
Sequential execution finishes the frame before the next. Review 3 compares this with stage overlap across frames.
No model training, plate localization or OCR is implemented. Changed pixels are not an accuracy score.""")

