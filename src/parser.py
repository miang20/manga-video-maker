from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import re
import yaml

@dataclass
class Scene:
    number: int
    text: str
    kind: str = "image"
    image_paths: list[Path] | None = None
    music: str | None = None
    image_hint: str = ""

def _num(name):
    m = re.match(r"^(\d+)[a-zA-Z]?\.(png|jpe?g|webp)$", name, re.I)
    return int(m.group(1)) if m else None

def _natural(p):
    return [int(x) if x.isdigit() else x.lower() for x in re.split(r"(\d+)", p.name)]

def _read_match_yaml(path: Path):
    if not path.is_file():
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must map scene numbers to image filenames.")
    mapping = data.get("scenes", data)
    if not isinstance(mapping, dict):
        raise ValueError(f"{path} must map scene numbers to image filenames.")
    return {int(k): [str(v)] if isinstance(v, str) else [str(item) for item in v]
            for k, v in mapping.items()}

def parse_script(project_dir: Path, image_matches=None):
    script = project_dir / "script.txt"
    if not script.is_file():
        raise FileNotFoundError(f"Missing script file: {script}")
    raw = script.read_text(encoding="utf-8-sig").replace("\r\n", "\n").strip()
    if not raw:
        raise ValueError(f"Script is empty: {script}")
    blocks = [b.strip() for b in re.split(r"\n\s*\n", raw) if b.strip()]
    folder = project_dir / "images"
    imgs = sorted([p for p in folder.glob("*") if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}], key=_natural) if folder.exists() else []
    scenes = []
    music = None
    for n, block in enumerate(blocks, 1):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if lines and lines[0].upper().startswith("MUSIC:"):
            music = lines.pop(0).split(":", 1)[1].strip()
            if not music:
                raise ValueError(f"Paragraph {n}: MUSIC: needs a track filename.")
            if not lines:
                continue
        hints = [line[4:].strip() for line in lines if line.upper().startswith("IMG:")]
        if len(hints) > 1:
            raise ValueError(f"Paragraph {n}: use at most one IMG: hint line.")
        body_lines = [line for line in lines if not line.upper().startswith("IMG:")]
        body = "\n".join(body_lines).strip()
        if body.upper().startswith("CARD:"):
            card = body.split(":", 1)[1].strip()
            if not card:
                raise ValueError(f"Paragraph {n}: CARD: is missing its text.")
            scenes.append(Scene(n, card, "card", [], music, hints[0] if hints else ""))
            music = None
            continue
        if not body:
            raise ValueError(f"Paragraph {n} has no spoken text after removing IMG: hints.")
        found = image_matches.get(n, []) if image_matches is not None else [p for p in imgs if _num(p.name) == n]
        found = [Path(p) if isinstance(p, (str, Path)) else p for p in found]
        if not found and image_matches is None:
            raise FileNotFoundError(f"Missing image for paragraph {n}: expected {n:02d}.png (or {n:02d}a.png, {n:02d}b.png, etc.) in {folder}")
        scenes.append(Scene(n, body, "image", found, music, hints[0] if hints else ""))
        music = None
    if not scenes:
        raise ValueError("No renderable paragraphs were found in script.txt.")
    return scenes
