from __future__ import annotations

import base64
import io
import re
import time
import zipfile
from pathlib import PurePosixPath

import requests
import streamlit as st

REPO = "miang20/manga-video-maker"
API = "https://api.github.com"
BRANCH = "main"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
VOICE_EXTS = {".mp3", ".wav", ".m4a", ".ogg"}
MAX_FILE_BYTES = 90 * 1024 * 1024

st.set_page_config(page_title="Manga Video Maker", page_icon="🎬", layout="centered")
st.markdown("""
<style>
.block-container {max-width: 850px; padding-top: 1.2rem; padding-bottom: 3rem}
.stButton>button, .stDownloadButton>button {min-height: 3.2rem; width:100%; font-size:1.05rem}
[data-testid="stFileUploader"] {border-radius:12px}
</style>
""", unsafe_allow_html=True)
st.title("🎬 Manga Video Maker")
st.caption("Phone-friendly front end • Rendering GitHub Actions par hoti hai — Streamlit par nahi.")

def api_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"}

def api(token: str, method: str, path: str, **kwargs):
    response = requests.request(method, API + path, headers=api_headers(token), timeout=90, **kwargs)
    if not response.ok:
        detail = ""
        try:
            detail = response.json().get("message", "")
        except Exception:
            pass
        raise RuntimeError(f"GitHub API error ({response.status_code}): {detail or 'request failed'}")
    if response.status_code == 204 or not response.content:
        return {}
    return response.json()

def safe_project(value: str) -> str:
    value = value.strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,70}", value) or value in {".", ".."}:
        raise ValueError("Project name mein letters, numbers, dot, underscore ya hyphen use karein.")
    return value

def list_tree(token: str, project: str):
    return api(token, "GET", f"/repos/{REPO}/git/trees/{BRANCH}?recursive=1").get("tree", [])

def delete_old_project_files(token: str, project: str):
    prefix = f"projects/{project}/"
    for item in list_tree(token, project):
        path = item.get("path", "")
        if path.startswith(prefix) and item.get("type") == "blob":
            api(token, "DELETE", f"/repos/{REPO}/contents/{path}",
                json={"message": f"Replace uploaded project {project}", "sha": item["sha"], "branch": BRANCH})

def upload_file(token: str, path: str, data: bytes, message: str):
    if len(data) > MAX_FILE_BYTES:
        raise ValueError(f"{PurePosixPath(path).name} 90 MB se bara hai; isay chhota karein.")
    body = {"message": message, "content": base64.b64encode(data).decode("ascii"), "branch": BRANCH}
    api(token, "PUT", f"/repos/{REPO}/contents/{path}", json=body)

def parse_paragraphs(script: str):
    blocks = re.split(r"\n\s*\n", script.strip())
    result = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        hints = [line[4:].strip() for line in lines if line.upper().startswith("IMG:")]
        spoken = [line for line in lines if not line.upper().startswith("IMG:")]
        if spoken:
            result.append({"text": " ".join(spoken), "hint": hints[0] if hints else ""})
    return result

def dispatch(token: str, project: str, preview: bool, settings: dict):
    return api(token, "POST", f"/repos/{REPO}/actions/workflows/render.yml/dispatches",
               json={"ref": BRANCH, "inputs": {"project": project, "preview_only": "true" if preview else "false",
                    "caption_mode": settings["caption_mode"], "caption_size": str(settings["caption_size"]),
                    "music_on": "true" if settings["music_on"] else "false",
                    "shorts_on": "true" if settings["shorts_on"] else "false",
                    "auto_match": "true" if settings["auto_match"] else "false"}})

def run_for_project(token: str, project: str, started: float):
    runs = api(token, "GET", f"/repos/{REPO}/actions/workflows/render.yml/runs?branch={BRANCH}&per_page=10").get("workflow_runs", [])
    candidates = [r for r in runs if r.get("created_at") and r.get("event") == "workflow_dispatch"
                  and r.get("created_at") >= time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started - 10))]
    return candidates[0] if candidates else None

def download_artifact(token: str, run_id: int):
    arts = api(token, "GET", f"/repos/{REPO}/actions/runs/{run_id}/artifacts").get("artifacts", [])
    artifact = next((a for a in arts if a.get("name", "").startswith("manga-video-") and not a.get("expired")), None)
    if not artifact:
        return None
    response = requests.get(artifact["archive_download_url"], headers=api_headers(token), timeout=180)
    if not response.ok:
        raise RuntimeError(f"Artifact download failed ({response.status_code}).")
    return zipfile.ZipFile(io.BytesIO(response.content))

def show_artifacts(archive: zipfile.ZipFile, project: str):
    names = archive.namelist()
    wanted = [f"{project}.mp4", f"{project}-shorts.mp4", f"{project}-thumbnail.png",
              f"{project}-match-preview.png", f"{project}.srt", "notes.txt", "match-table.txt", "first-error.txt"]
    lookup = {PurePosixPath(n).name: n for n in names if not n.endswith("/")}
    for name in wanted:
        member = lookup.get(name)
        if not member:
            continue
        data = archive.read(member)
        if name.lower().endswith(".png") and "match-preview" in name:
            st.subheader("Image order preview")
            st.image(data, use_container_width=True)
        if name.lower().endswith((".mp4", ".png", ".srt", ".txt")):
            mime = "video/mp4" if name.endswith(".mp4") else "image/png" if name.endswith(".png") else "text/plain"
            st.download_button(f"Download {name}", data, file_name=name, mime=mime, key=f"dl-{member}")
        if "match-table" in name or name == "notes.txt":
            st.subheader("Match table / notes")
            st.code(data.decode("utf-8", errors="replace")[:20000])
        if name == "first-error.txt":
            st.error("Workflow error (simple details)")
            st.code(data.decode("utf-8", errors="replace")[:6000])

try:
    token = st.secrets["GITHUB_TOKEN"]
except Exception:
    token = ""

if not token:
    st.warning("Streamlit Community Cloud → App settings → Secrets mein GITHUB_TOKEN add karein.")
    st.code('GITHUB_TOKEN = "github_pat_your_token_here"')

try:
    recent = api(token, "GET", f"/repos/{REPO}/contents/projects?ref={BRANCH}") if token else []
    existing = [x["name"] for x in recent if x.get("type") == "dir"] if isinstance(recent, list) else []
except Exception:
    existing = []
default_project = f"video-{len(existing) + 1:03d}"
project_name = st.text_input("Project name", value=st.session_state.get("project_name", default_project), max_chars=71)
script_upload = st.file_uploader("1. script.txt (optional if you paste below)", type=["txt"], key="script_upload")
script_paste = st.text_area("Or paste your script here", height=160, placeholder="Har paragraph ke darmiyan blank line rakhein. Optional hint: IMG: rainy street at night")
script_text = script_upload.getvalue().decode("utf-8", errors="replace") if script_upload else script_paste
paragraphs = parse_paragraphs(script_text) if script_text.strip() else []
st.subheader("2. Images — any filenames, any order")
images = st.file_uploader("Select all scene images", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True, key="images")
voice = st.file_uploader("3. Voice file (required for full render)", type=sorted(VOICE_EXTS), key="voice")
music = st.file_uploader("Optional background music", type=["mp3", "wav", "m4a", "ogg"], key="music")

if paragraphs:
    st.subheader("Image hints (optional)")
    st.caption("Har paragraph ke neeche chhota visual hint likhein. Ye IMG: lines ke saath upload hongay.")
    edited = []
    for i, para in enumerate(paragraphs, 1):
        st.markdown(f"**Paragraph {i}:** {para['text'][:220]}")
        hint = st.text_input(f"Image hint {i}", value=para["hint"], key=f"hint-{i}")
        edited.append({"text": para["text"], "hint": hint})
    if st.button("Apply hints to script"):
        script_text = "\n\n".join(p["text"] + (("\nIMG: " + p["hint"]) if p["hint"] else "") for p in edited)
        st.session_state["script_with_hints"] = script_text
        st.success("Hints ready. Render ke waqt apply hongay.")
if st.session_state.get("script_with_hints"):
    script_text = st.session_state["script_with_hints"]

with st.expander("Settings", expanded=True):
    caption_mode = st.radio("Caption mode", ["overlay", "card"], horizontal=True, index=0)
    caption_size = st.slider("Caption size", 24, 72, 48, 2)
    music_on = st.toggle("Background music on", value=True)
    shorts_on = st.toggle("Create vertical Shorts", value=True)
    auto_match = st.toggle("Auto-match images to script", value=True)

st.info("Note: large uploads are sent to GitHub Contents API. Per-file app limit is 90 MB; GitHub's API also has practical limits.")
def start_job(preview: bool):
    if not token:
        st.error("GITHUB_TOKEN missing hai. Secrets configure karein.")
        return
    try:
        name = safe_project(project_name)
        st.session_state["project_name"] = name
        if not script_text.strip():
            raise ValueError("Pehle script upload ya paste karein.")
        if not images:
            raise ValueError("Kam az kam 1 image select karein.")
        if not preview and not voice:
            raise ValueError("Full render ke liye voice file upload karein.")
        uploads = [("script.txt", script_text.encode("utf-8"))]
        for f in images:
            if PurePosixPath(f.name).suffix.lower() not in IMAGE_EXTS:
                continue
            uploads.append(("images/" + PurePosixPath(f.name).name, f.getvalue()))
        if voice:
            uploads.append(("voice" + PurePosixPath(voice.name).suffix.lower(), voice.getvalue()))
        if music and music_on:
            uploads.append(("music" + PurePosixPath(music.name).suffix.lower(), music.getvalue()))
        st.session_state["active_run_started"] = time.time()
        st.session_state["active_project"] = name
        st.session_state["active_preview"] = preview
        with st.status("GitHub par project upload ho raha hai…", expanded=True) as status:
            delete_old_project_files(token, name)
            for filename, data in uploads:
                upload_file(token, f"projects/{name}/{filename}", data, f"Upload {name} project input")
                st.write(f"Uploaded: {filename}")
            settings = {"caption_mode": caption_mode, "caption_size": caption_size, "music_on": music_on,
                        "shorts_on": shorts_on, "auto_match": auto_match}
            dispatch(token, name, preview, settings)
            status.update(label="Workflow dispatch request sent", state="complete")
        st.session_state["watch_run"] = True
    except Exception as exc:
        st.error(f"Request complete nahi hui: {exc}")

c1, c2 = st.columns(2)
with c1:
    if st.button("🚀 Render full video", type="primary", use_container_width=True):
        start_job(False)
with c2:
    if st.button("🖼️ Preview image order only", use_container_width=True):
        start_job(True)

if st.session_state.get("watch_run") and token:
    name = st.session_state.get("active_project", "")
    started = st.session_state.get("active_run_started", time.time())
    st.subheader("Workflow status")
    status_box = st.empty()
    link_box = st.empty()
    run = None
    for attempt in range(180):
        try:
            run = run_for_project(token, name, started)
            if run:
                state = run.get("status", "queued")
                conclusion = run.get("conclusion")
                url = run.get("html_url", f"https://github.com/{REPO}/actions")
                link_box.markdown(f"[Open GitHub Actions run]({url})")
                if state == "completed":
                    if conclusion == "success":
                        status_box.success("Success — workflow complete.")
                    else:
                        status_box.error("Failed — GitHub Actions run open karein; artifact mein first-error.txt ho sakti hai.")
                    archive = download_artifact(token, int(run["id"]))
                    if archive:
                        show_artifacts(archive, name)
                    else:
                        st.info("Artifact abhi available nahi. Run complete hone ke baad refresh karein.")
                    st.session_state["watch_run"] = False
                    break
                status_box.info("Queued — runner ka wait ho raha hai." if state == "queued" else "Running — GitHub Actions rendering kar raha hai.")
            else:
                status_box.info("Workflow dispatch ho gaya; run register hone ka wait hai.")
        except Exception as exc:
            status_box.warning(f"Status fetch temporarily unavailable: {exc}")
        time.sleep(10)
    else:
        st.info("Monitoring pause hui. Page refresh karein; GitHub Actions run continue karega.")
