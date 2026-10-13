from __future__ import annotations
import shutil,tempfile,zipfile
from pathlib import Path
import streamlit as st,yaml
from render import render_project
from src.utils import ROOT
from src.shorts import make_shorts
st.set_page_config(page_title="Manga Video Maker",page_icon="🎬")
st.title("Manga Video Maker");st.write("Upload script.txt and a ZIP of numbered images, render, preview and download.")
script=st.file_uploader("1. Upload script.txt",type=["txt"]);images=st.file_uploader("2. Upload numbered images ZIP",type=["zip"])
voices={"Guy (US male)":"en-US-GuyNeural","Jenny (US female)":"en-US-JennyNeural","Aria (US female)":"en-US-AriaNeural","Ryan (UK male)":"en-GB-RyanNeural"}
voice=st.selectbox("Voice",list(voices));shorts=st.checkbox("Also create vertical Shorts cut")
start=st.number_input("Shorts start seconds",min_value=0.0,value=0.0,disabled=not shorts);end=st.number_input("Shorts end seconds",min_value=1.0,value=30.0,disabled=not shorts)
if st.button("Render video",type="primary",disabled=not(script and images)):
 try:
  with tempfile.TemporaryDirectory(prefix="manga-video-") as tmp:
   project=Path(tmp)/"uploaded-project";(project/"images").mkdir(parents=True);(project/"script.txt").write_bytes(script.getvalue())
   with zipfile.ZipFile(images) as z:
    for info in z.infolist():
     p=Path(info.filename)
     if info.is_dir() or p.suffix.lower() not in {".png",".jpg",".jpeg",".webp"}:continue
     if p.is_absolute() or ".." in p.parts:raise ValueError("ZIP contains an unsafe file path.")
     with z.open(info) as src,(project/"images"/p.name).open("wb") as dst:shutil.copyfileobj(src,dst)
   cfg=yaml.safe_load((ROOT/"config.yaml").read_text());cfg["voice"]["name"]=voices[voice];cp=Path(tmp)/"config.yaml";cp.write_text(yaml.safe_dump(cfg,sort_keys=False))
   with st.spinner("Generating voice and rendering..."):
    out=render_project(project,cp);data=out.read_bytes()
   st.success("Render complete.");st.video(data);st.download_button("Download MP4",data,file_name="manga-video.mp4",mime="video/mp4")
   if shorts:
    short=Path(tmp)/"shorts.mp4";make_shorts(out,short,start,end);st.download_button("Download vertical Shorts",short.read_bytes(),file_name="manga-video-shorts.mp4",mime="video/mp4")
 except Exception as e:st.error(str(e))
