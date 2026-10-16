import os
import subprocess
from pathlib import Path
from src.sample_assets import ensure_sample_project, ensure_test_voice, ensure_thumbnail

name = os.environ["PROJECT_INPUT"].strip()
if not name or "/" in name or chr(92) in name or name in {".", ".."}:
    raise SystemExit("Project must be one folder name such as video-001.")
project = Path("projects") / name
if name == "video-001":
    ensure_sample_project(project)
ensure_thumbnail(project, Path("output"))
if not (project / "script.txt").is_file():
    raise SystemExit(f"Missing script file: {project / 'script.txt'}")
voice_paths = [project / f"voice{ext}" for ext in (".mp3", ".wav", ".m4a", ".ogg")]
generated_voice = not any(path.is_file() and path.stat().st_size for path in voice_paths)
if generated_voice:
    ensure_test_voice(project)
    with Path(os.environ["GITHUB_ENV"]).open("a", encoding="utf-8") as env_file:
        env_file.write("SELF_TEST_MODE=true\n")
    print("SELF_TEST_MODE=PASS; generated offline test voice")
else:
    with Path(os.environ["GITHUB_ENV"]).open("a", encoding="utf-8") as env_file:
        env_file.write("SELF_TEST_MODE=false\n")
    print("SELF_TEST_MODE=PASS; uploaded voice found")
music_dir = Path("assets/music")
music_dir.mkdir(parents=True, exist_ok=True)
has_music = any(path.is_file() and path.suffix.lower() == ".mp3" for path in music_dir.iterdir())
pad = music_dir / "000-self-test-pad.mp3"
if generated_voice or not has_music:
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i",
        "aevalsrc=0.020*sin(2*PI*110*t)+0.015*sin(2*PI*164.81*t)+0.010*sin(2*PI*220*t):s=44100:d=120",
        "-af", "lowpass=f=900,afade=t=in:st=0:d=2,afade=t=out:st=115:d=5",
        "-codec:a", "libmp3lame", "-b:a", "96k", str(pad)
    ], check=True, capture_output=True, text=True)
    print(f"MUSIC_PAD_GENERATED={pad}")
image_files = [path for path in (project / "images").glob("*")
               if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}]
if name == "video-001" and len(image_files) < 4:
    raise SystemExit(f"Sample project needs at least 4 numbered images; found {len(image_files)}")
print(f"SAMPLE_IMAGES_COUNT={len(image_files)}")
print(f"PROJECT_READY={project}")
