from __future__ import annotations
import re
import shutil
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw

SAMPLE_SCRIPT = """On a silent night, a lone warrior hears something move behind the wall.

The shadow stretches across the floor, but nobody is standing there.

He raises his blade slowly, trying not to make a sound.

Then the door opens by itself, revealing a hallway with no end.

One tiny footprint appears in the dust. It is facing him.
"""
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
VOICE_EXTENSIONS = (".mp3", ".wav", ".m4a", ".ogg")

def _scene_count(project: Path) -> int:
    script = project / "script.txt"
    if not script.is_file():
        return 5
    raw = script.read_text(encoding="utf-8-sig").strip()
    blocks = [block.strip() for block in re.split(r"\n\s*\n", raw) if block.strip()]
    count = sum(1 for block in blocks if not all(
        line.strip().upper().startswith("MUSIC:") for line in block.splitlines() if line.strip()
    ))
    return max(1, count)

def ensure_sample_images(project: Path, count: int | None = None) -> None:
    folder = project / "images"
    folder.mkdir(parents=True, exist_ok=True)
    for number in range(1, max(1, int(count or _scene_count(project))) + 1):
        path = folder / f"{number:02d}.png"
        if path.exists():
            continue
        image = Image.new("RGB", (1280, 720), "black")
        draw = ImageDraw.Draw(image)
        x, y, width = 640, 360, 7
        white, gray = (245, 245, 245), (85, 85, 85)
        draw.ellipse((x-52, y-210, x+52, y-106), outline=white, width=width)
        draw.line((x, y-106, x, y+70), fill=white, width=width)
        draw.line((x, y-55, x-100, y+5), fill=white, width=width)
        draw.line((x, y-55, x+100, y-5), fill=white, width=width)
        draw.line((x, y+70, x-78, y+200), fill=white, width=width)
        draw.line((x, y+70, x+78, y+200), fill=white, width=width)
        if number % 5 == 1:
            draw.arc((x+125, y-55, x+275, y+85), 180, 300, fill=gray, width=5)
        elif number % 5 == 2:
            draw.line((x+140, y-170, x+250, y-210, x+295, y-80), fill=gray, width=5)
        elif number % 5 == 3:
            draw.line((x-250, y+160, x+250, y+160), fill=gray, width=5)
        elif number % 5 == 4:
            draw.rectangle((x+150, y-230, x+300, y+180), outline=gray, width=5)
        else:
            draw.ellipse((x-265, y+160, x-205, y+220), outline=white, width=5)
        image.save(path, optimize=True)

def ensure_sample_project(project: Path) -> None:
    project.mkdir(parents=True, exist_ok=True)
    if project.name == "video-001" and not (project / "script.txt").is_file():
        (project / "script.txt").write_text(SAMPLE_SCRIPT, encoding="utf-8")
    ensure_sample_images(project)
    thumbnail_dir = project / "thumbnail"
    thumbnail_dir.mkdir(parents=True, exist_ok=True)
    if not any(p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS for p in thumbnail_dir.iterdir()):
        first = project / "images" / "01.png"
        if first.is_file():
            shutil.copy2(first, thumbnail_dir / "sample-thumbnail.png")

def ensure_thumbnail(project: Path, output_dir: Path) -> Path:
    """Create a thumbnail if needed and always copy one to the artifact output directory."""
    project = Path(project)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    thumbnail_dir = project / "thumbnail"
    thumbnail_dir.mkdir(parents=True, exist_ok=True)
    candidates = sorted(
        (p for p in thumbnail_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS),
        key=lambda p: p.name.lower(),
    )
    if not candidates:
        image_dir = project / "images"
        source_image = next(
            (p for p in sorted(image_dir.iterdir(), key=lambda p: p.name.lower())
             if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS),
            None,
        ) if image_dir.is_dir() else None
        destination = thumbnail_dir / f"{project.name}-thumbnail.png"
        if source_image:
            shutil.copy2(source_image, destination)
        else:
            image = Image.new("RGB", (1280, 720), "black")
            draw = ImageDraw.Draw(image)
            draw.text((64, 320), project.name, fill="white")
            image.save(destination)
        candidates = [destination]
    source = candidates[0]
    target = output_dir / f"{project.name}-thumbnail{source.suffix.lower()}"
    shutil.copy2(source, target)
    print(f"THUMBNAIL_READY={target}")
    return target


def find_voice_file(project: Path) -> Path | None:
    for extension in VOICE_EXTENSIONS:
        candidate = project / f"voice{extension}"
        if candidate.is_file() and candidate.stat().st_size:
            return candidate
    return None

def ensure_test_voice(project: Path) -> Path:
    existing = find_voice_file(project)
    if existing:
        return existing
    script = project / "script.txt"
    if not script.is_file():
        raise FileNotFoundError(f"Missing script file for offline narration: {script}")
    text = " ".join(line.strip() for line in script.read_text(encoding="utf-8-sig").splitlines() if line.strip() and not line.strip().upper().startswith("IMG:"))
    if not text:
        raise ValueError(f"Script is empty: {script}")
    if not shutil.which("espeak-ng") or not shutil.which("ffmpeg"):
        raise RuntimeError("Offline sample narration requires espeak-ng and FFmpeg; the workflow installs both.")
    work = project / "work"
    work.mkdir(parents=True, exist_ok=True)
    source_wav, target = work / "sample-voice-source.wav", project / "voice.mp3"
    subprocess.run(["espeak-ng", "-v", "en-us", "-s", "145", "-w", str(source_wav), text],
                   check=True, capture_output=True, text=True)
    subprocess.run(["ffmpeg", "-y", "-i", str(source_wav), "-af", "adelay=1500|1500",
                    "-ar", "22050", "-ac", "2", "-codec:a", "libmp3lame", "-b:a", "96k", str(target)],
                   check=True, capture_output=True, text=True)
    source_wav.unlink(missing_ok=True)
    if not target.is_file() or target.stat().st_size < 1000:
        raise RuntimeError("Offline sample narration was not generated.")
    print(f"TEST_VOICE_GENERATED={target} (1.5s leading silence, 22050 Hz MP3)")
    return target
