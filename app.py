from __future__ import annotations

import base64
import calendar
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
def natural_key(name: str):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", name)]
VOICE_EXTS = {".mp3", ".wav", ".m4a", ".ogg"}
MAX_FILE_BYTES = 25 * 1024 * 1024

st.set_page_config(page_title="Master Video Maker", page_icon="🎬", layout="centered")
st.markdown("""
<style>
.block-container {max-width: 850px; padding-top: 1.2rem; padding-bottom: 3rem}
.stButton>button, .stDownloadButton>button {min-height: 3.2rem; width:100%; font-size:1.05rem}
[data-testid="stFileUploader"] {border-radius:12px}
</style>
""", unsafe_allow_html=True)
st.title("🎬 Master Video Maker")
st.caption("Phone-friendly front end • Rendering GitHub Actions par hoti hai — Streamlit par nahi.")

def api_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"}

def api(token: str, method: str, path: str, **kwargs):
    last_error = None
    attempts = 2 if method.upper() in {"GET", "DELETE"} else 1
    for attempt in range(attempts):
        try:
            response = requests.request(method, API + path, headers=api_headers(token), timeout=90, **kwargs)
            if response.ok:
                if response.status_code == 204 or not response.content:
                    return {}
                return response.json()
            try:
                detail = response.json().get("message", "")
            except Exception:
                detail = ""
            last_error = RuntimeError(f"GitHub API error ({response.status_code}): {detail or 'request failed'}")
            if response.status_code < 500 and response.status_code != 429:
                raise last_error
        except requests.RequestException as exc:
            last_error = exc
        if attempt == 0:
            time.sleep(1.5)
    raise RuntimeError(f"GitHub request failed: {last_error}") from last_error
def safe_project(value: str) -> str:
    value = value.strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,70}", value) or value in {".", ".."}:
        raise ValueError("Project name mein letters, numbers, dot, underscore ya hyphen use karein.")
    return value

def list_tree(token: str, project: str):
    return api(token, "GET", f"/repos/{REPO}/git/trees/{BRANCH}?recursive=1")

def delete_old_project_files(token: str, project: str):
    prefix = f"projects/{project}/"
    tree = list_tree(token, project)
    if tree.get("truncated"):
        raise RuntimeError("GitHub ki project file list incomplete hai; safety ke liye upload roka gaya.")
    for item in tree.get("tree", []):
        path = item.get("path", "")
        if path.startswith(prefix) and item.get("type") == "blob":
            api(token, "DELETE", f"/repos/{REPO}/contents/{path}",
                json={"message": f"Replace uploaded project {project}", "sha": item["sha"], "branch": BRANCH})

def upload_file(token: str, path: str, data: bytes, message: str):
    if len(data) > MAX_FILE_BYTES:
        raise ValueError(f"{PurePosixPath(path).name} {len(data) / (1024 * 1024):.1f} MB hai; maximum 25 MB per file hai.")
    endpoint = f"/repos/{REPO}/contents/{path}"
    encoded = base64.b64encode(data).decode("ascii")
    for attempt in range(2):
        body = {"message": message, "content": encoded, "branch": BRANCH}
        try:
            api(token, "PUT", endpoint, json=body)
            return
        except (RuntimeError, requests.RequestException):
            if attempt:
                raise
            try:
                current = api(token, "GET", endpoint + f"?ref={BRANCH}")
                if current.get("type") == "file" and current.get("sha"):
                    body["sha"] = current["sha"]
                    api(token, "PUT", endpoint, json=body)
                    return
            except RuntimeError:
                pass
            time.sleep(1)
    raise RuntimeError(f"{PurePosixPath(path).name} upload nahi hui; file dobara try karein.")
def parse_paragraphs(script: str):
    blocks = re.split(r"\n\s*\n", script.strip())
    result = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        spoken = [line for line in lines if not line.upper().startswith("IMG:")]
        if spoken:
            text = " ".join(spoken)
            result.append({"text": text, "is_card": text.upper().startswith("CARD:")})
    return result

def dispatch(token: str, project: str, preview: bool, settings: dict):
    return api(token, "POST", f"/repos/{REPO}/actions/workflows/render.yml/dispatches",
               json={"ref": BRANCH, "inputs": {"project": project, "preview_only": "true" if preview else "false",
                    "caption_mode": settings["caption_mode"], "caption_size": str(settings["caption_size"]),
                    "music_on": "true" if settings["music_on"] else "false",
                    "shorts_on": "true" if settings["shorts_on"] else "false",
                    "voice_source": settings["voice_source"], "voice": settings["voice"],
                    "voice_speed": str(settings["voice_speed"]), "style": settings["style"],
                    "motion_intensity": settings["motion_intensity"]}})

def run_for_project(token: str, project: str, started: float):
    runs = api(token, "GET", f"/repos/{REPO}/actions/workflows/render.yml/runs?branch={BRANCH}&event=workflow_dispatch&per_page=30").get("workflow_runs", [])
    cutoff = started - 3
    candidates = []
    for run in runs:
        created = run.get("created_at")
        if not created:
            continue
        try:
            created_epoch = calendar.timegm(time.strptime(created, "%Y-%m-%dT%H:%M:%SZ"))
        except ValueError:
            continue
        title = str(run.get("display_title") or run.get("name") or "")
        if created_epoch >= cutoff and project in title:
            candidates.append(run)
    return max(candidates, key=lambda r: r.get("created_at", "")) if candidates else None
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
    files = [n for n in names if not n.endswith("/")]
    thumbnail_member = next((n for n in files if PurePosixPath(n).name.startswith(project + "-thumbnail.")), None)
    wanted = [f"{project}.mp4", f"{project}-shorts.mp4"]
    if thumbnail_member:
        wanted.append(PurePosixPath(thumbnail_member).name)
    wanted.extend([f"{project}-match-preview.png", f"{project}.srt", "notes.txt", "match-table.txt", "first-error.txt"])
    lookup = {PurePosixPath(n).name: n for n in files}
    for name in wanted:
        member = lookup.get(name)
        if not member:
            continue
        data = archive.read(member)
        if name.lower().endswith(".png") and "match-preview" in name:
            st.subheader("Image order preview")
            st.image(data, use_container_width=True)
        if name.lower().endswith((".mp4", ".png", ".jpg", ".jpeg", ".srt", ".txt")):
            mime = "video/mp4" if name.endswith(".mp4") else "image/png" if name.endswith(".png") else "image/jpeg" if name.endswith((".jpg", ".jpeg")) else "text/plain"
            st.download_button(f"Download {name}", data, file_name=name, mime=mime, key=f"dl-{member}")
        if "match-table" in name or name == "notes.txt":
            st.subheader("Match table / notes")
            st.code(data.decode("utf-8", errors="replace")[:20000])
        if name == "first-error.txt":
            st.error("Workflow error (simple details)")
            st.code(data.decode("utf-8", errors="replace")[:6000])
    if not any(PurePosixPath(n).name == "first-error.txt" for n in files):
        st.caption("Artifact mein first-error.txt nahi mili.")
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
script_paste = st.text_area("Or paste your script here", height=160, placeholder="Har paragraph ke darmiyan blank line rakhein. Images filename ke natural order mein use hongi.")
script_text = script_upload.getvalue().decode("utf-8", errors="replace") if script_upload else script_paste
paragraphs = parse_paragraphs(script_text) if script_text.strip() else []
st.subheader("2. Images — natural filename order")
images = st.file_uploader("Select all scene images", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True, key="images")
with st.expander("Voice and visual settings", expanded=True):
    voice_source = st.selectbox("Voice source", ["upload", "kokoro"], index=0)
    voice_options = ["af_heart", "af_alloy", "af_aoede", "af_bella", "af_jessica", "af_kore", "af_nicole", "af_nova", "af_river", "af_sarah", "af_sky", "am_adam", "am_echo", "am_eric", "am_fenrir", "am_liam", "am_michael", "am_onyx", "am_puck", "am_santa", "bf_alice", "bf_emma", "bf_isabella", "bf_lily", "bm_daniel", "bm_fable", "bm_george", "bm_lewis"]
    kokoro_voice = st.selectbox("Kokoro English voice", voice_options, index=0, disabled=voice_source != "kokoro")
    voice_speed = st.slider("Voice speed", 0.7, 1.3, 1.0, 0.05, disabled=voice_source != "kokoro")
    style = st.selectbox("Image style", ["bw_manga", "color", "clean"], index=0)
    motion_intensity = st.selectbox("Motion intensity", ["subtle", "normal", "strong"], index=1)
voice = st.file_uploader("3. Voice file (not needed in Kokoro mode)", type=sorted(VOICE_EXTS), key="voice")
music = st.file_uploader("Optional background music", type=["mp3", "wav", "m4a", "ogg"], key="music")

ordered_images = sorted(
    [f for f in (images or []) if PurePosixPath(f.name).suffix.lower() in IMAGE_EXTS],
    key=lambda f: natural_key(PurePosixPath(f.name).name),
)
image_paragraphs = [(i, p) for i, p in enumerate(paragraphs, 1) if not p.get("is_card")]
if paragraphs:
    st.subheader("Image-to-paragraph order preview")
    st.caption("Natural filename order is fixed. No automatic matching or reordering is performed.")
    if len(ordered_images) != len(image_paragraphs):
        st.warning(f"Image count mismatch: {len(ordered_images)} images for {len(image_paragraphs)} image paragraphs. Add/remove images before rendering.")
    for index, (paragraph_number, para) in enumerate(image_paragraphs):
        if index >= len(ordered_images):
            st.warning(f"Paragraph {paragraph_number}: image missing.")
            continue
        image_file = ordered_images[index]
        left, right = st.columns([1, 2])
        with left:
            st.image(image_file.getvalue(), caption=f"Paragraph {paragraph_number} · {PurePosixPath(image_file.name).name}", use_container_width=True)
        with right:
            st.markdown(f"**Paragraph {paragraph_number}**")
            st.write(para["text"][:350])

with st.expander("Settings", expanded=True):
    caption_mode = st.radio("Caption mode", ["overlay", "card"], horizontal=True, index=0)
    caption_size = st.slider("Caption size", 40, 100, 76, 2)
    music_on = st.toggle("Background music on", value=True)
    shorts_on = st.toggle("Create vertical Shorts", value=True)

st.info("Note: large uploads are sent to GitHub Contents API. Per-file app limit is 25 MB; GitHub's API also has practical limits.")
def start_job(preview: bool):
    if not token:
        st.error("GITHUB_TOKEN missing hai. Secrets configure karein.")
        return
    try:
        name = safe_project(project_name)
        st.session_state["project_name"] = name
        if not script_text.strip():
            raise ValueError("Pehle script upload ya paste karein.")
        if not ordered_images:
            raise ValueError("Kam az kam 1 image select karein.")
        if len(ordered_images) != len(image_paragraphs):
            raise ValueError(f"Image count mismatch: {len(ordered_images)} images for {len(image_paragraphs)} image paragraphs. Rendering stopped; count must match exactly.")
        if not preview and voice_source == "upload" and not voice:
            raise ValueError("Upload mode mein voice file required hai; Kokoro mode mein upload zaroori nahi.")
        uploads = [("script.txt", script_text.encode("utf-8"))]
        for f in ordered_images:
            if PurePosixPath(f.name).suffix.lower() not in IMAGE_EXTS:
                continue
            uploads.append(("images/" + PurePosixPath(f.name).name, f.getvalue()))
        if voice and voice_source == "upload":
            uploads.append(("voice" + PurePosixPath(voice.name).suffix.lower(), voice.getvalue()))
        if music and music_on:
            uploads.append(("music" + PurePosixPath(music.name).suffix.lower(), music.getvalue()))
        oversized = [(filename, len(data)) for filename, data in uploads if len(data) > MAX_FILE_BYTES]
        if oversized:
            filename, size = oversized[0]
            raise ValueError(f"{filename} {size / (1024 * 1024):.1f} MB hai. Maximum 25 MB per file hai; compress karein.")
        st.session_state["active_project"] = name
        st.session_state["active_preview"] = preview
        with st.status("GitHub par project upload ho raha hai…", expanded=True) as status:
            delete_old_project_files(token, name)
            for filename, data in uploads:
                upload_file(token, f"projects/{name}/{filename}", data, f"Upload {name} project input")
                st.write(f"Uploaded: {filename}")
            settings = {"caption_mode": caption_mode, "caption_size": caption_size, "music_on": music_on,
                        "shorts_on": shorts_on}
            st.session_state["active_run_started"] = time.time()
            dispatch(token, name, preview, settings)
            status.update(label="Workflow dispatch request sent", state="complete")
        st.session_state["watch_run"] = True
    except Exception as exc:
        st.error(f"Request complete nahi hui: {exc}")

if st.button("🚀 Render full video", type="primary", use_container_width=True):
    start_job(False)

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
