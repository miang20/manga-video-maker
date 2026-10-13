from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import yaml
from PIL import Image, ImageDraw, ImageFont
from scipy.optimize import linear_sum_assignment
from sentence_transformers import SentenceTransformer
from src.parser import Scene, _natural

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
MODEL_NAME = "clip-ViT-B-32"

def _blocks(project: Path):
    raw = (project / "script.txt").read_text(encoding="utf-8-sig").replace("\r\n", "\n").strip()
    blocks = [b.strip() for b in re.split(r"\n\s*\n", raw) if b.strip()]
    output = []
    for number, block in enumerate(blocks, 1):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if lines and lines[0].upper().startswith("MUSIC:"):
            lines.pop(0)
            if not lines:
                continue
        hints = [line[4:].strip() for line in lines if line.upper().startswith("IMG:")]
        spoken = " ".join(line for line in lines if not line.upper().startswith("IMG:"))
        if spoken.upper().startswith("CARD:") or not spoken.strip():
            continue
        output.append((number, spoken.strip(), hints[0] if hints else ""))
    return output

def _manual_mapping(project: Path, scenes, images):
    path = project / "match.yaml"
    if not path.is_file():
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("match.yaml must map scene numbers to image filenames.")
    mapping = data.get("scenes", data)
    if not isinstance(mapping, dict):
        raise ValueError("match.yaml must map scene numbers to image filenames.")
    by_name = {p.name: p for p in images}
    result = {scene.number: [] for scene in scenes}
    used = set()
    for key, value in mapping.items():
        number = int(key)
        if number not in result:
            raise ValueError(f"match.yaml refers to unknown scene {number}.")
        names = [value] if isinstance(value, str) else value
        if not isinstance(names, list):
            raise ValueError(f"match.yaml scene {number} must have a filename or list of filenames.")
        for name in names:
            name = str(name)
            if name not in by_name:
                raise ValueError(f"match.yaml scene {number} references missing image: {name}")
            if name in used:
                raise ValueError(f"match.yaml assigns image {name} more than once.")
            result[number].append(by_name[name])
            used.add(name)
    return result

def _confidence(scores, image_index):
    if scores.size <= 1:
        return 1.0
    ordered = np.sort(scores[:, image_index])
    best = float(ordered[-1])
    second = float(ordered[-2])
    return max(0.0, min(1.0, (best - second + 1.0) / 2.0))

def match_project(project: Path, scenes: list[Scene], output_dir: Path, config: dict | None = None):
    """Assign images to scenes with CLIP embeddings and Hungarian matching; return mapping and report."""
    project = Path(project)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    folder = project / "images"
    images = sorted((p for p in folder.glob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS), key=_natural) if folder.exists() else []
    image_scenes = [s for s in scenes if s.kind == "image"]
    manual = _manual_mapping(project, image_scenes, images)
    rows = []
    mapping = {scene.number: [] for scene in image_scenes}
    if manual is not None:
        mapping.update(manual)
        for scene in image_scenes:
            names = mapping[scene.number]
            rows.append({"scene": scene.number, "text": scene.text, "images": names, "score": None, "confidence": "MANUAL"})
        print("MATCH_MODE=manual (match.yaml found; automatic matching skipped)")
    else:
        if not images:
            for scene in image_scenes:
                print(f"WARNING: scene {scene.number} has no image; continuing with no visual.")
                rows.append({"scene": scene.number, "text": scene.text, "images": [], "score": None, "confidence": "NO IMAGE"})
        else:
            model_name = (config or {}).get("matcher", {}).get("model", MODEL_NAME)
            cache = str((config or {}).get("matcher", {}).get("model_cache", "~/.cache/huggingface/hub"))
            import os
            os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", str(Path(cache).expanduser().parent))
            model = SentenceTransformer(model_name, device="cpu", cache_folder=str(Path(cache).expanduser()))
            scene_texts = [scene.image_hint.strip() or scene.text for scene in image_scenes]
            image_vectors = model.encode([__import__("PIL").Image.open(p).convert("RGB") for p in images],
                                         batch_size=4, convert_to_numpy=True, normalize_embeddings=True,
                                         show_progress_bar=True)
            text_vectors = model.encode(scene_texts, batch_size=8, convert_to_numpy=True,
                                        normalize_embeddings=True, show_progress_bar=True)
            similarities = np.matmul(text_vectors, image_vectors.T)
            row_indices, col_indices = linear_sum_assignment(-similarities)
            for ri, ci in zip(row_indices.tolist(), col_indices.tolist()):
                mapping[image_scenes[ri].number].append(images[ci])
            # Extra images are attached to their highest-scoring scene after one-to-one assignment.
            assigned = set(col_indices.tolist())
            for ci, image in enumerate(images):
                if ci in assigned:
                    continue
                ri = int(np.argmax(similarities[:, ci]))
                mapping[image_scenes[ri].number].append(image)
            for ri, scene in enumerate(image_scenes):
                chosen = mapping[scene.number]
                best_score = max((float(similarities[ri, images.index(path)]) for path in chosen), default=None)
                sorted_scores = np.sort(similarities[:, images.index(chosen[0])]) if chosen else np.array([])
                if chosen and len(sorted_scores) > 1:
                    gap = float(sorted_scores[-1] - sorted_scores[-2])
                    confidence = "LOW" if gap < 0.035 else "MEDIUM" if gap < 0.08 else "HIGH"
                else:
                    confidence = "HIGH" if chosen else "NO IMAGE"
                rows.append({"scene": scene.number, "text": scene.text, "images": chosen, "score": best_score, "confidence": confidence})
                if not chosen:
                    print(f"WARNING: scene {scene.number} has no image; continuing with no visual.")
            low = [row["scene"] for row in rows if row["confidence"] == "LOW"]
            if low:
                print("\n" + "!" * 24 + f" WARNING: LOW-CONFIDENCE IMAGE MATCHES FOR SCENES {', '.join(map(str, low))} " + "!" * 24 + "\n")
            print(f"AUTO_MATCH_MODEL={model_name}; similarity matrix={similarities.shape}; assigned images at most once before extras")
    # Apply image mapping and write a transparent scene-level report.
    by_number = {scene.number: scene for scene in image_scenes}
    for number, paths in mapping.items():
        by_number[number].image_paths = list(paths)
    lines = ["Scene | first 6 words | matched image | similarity score | confidence",
             "--- | --- | --- | --- | ---"]
    for row in rows:
        words = " ".join(row["text"].split()[:6]).replace("|", "/")
        names = ", ".join(path.name for path in row["images"]) if row["images"] else "(none)"
        score = f"{row['score']:.3f}" if isinstance(row["score"], (int, float)) else "-"
        lines.append(f"{row['scene']} | {words} | {names} | {score} | {row['confidence']}")
    table = "\n".join(lines)
    print("\nIMAGE SCENE MATCH TABLE\n" + table)
    notes = output_dir / "notes.txt"
    notes.parent.mkdir(parents=True, exist_ok=True)
    with notes.open("a", encoding="utf-8") as handle:
        handle.write("\n\nIMAGE SCENE MATCH TABLE\n" + table + "\n")
    _write_contact_sheet(rows, output_dir / f"{project.name}-match-preview.png")
    return mapping, rows

def _write_contact_sheet(rows, destination: Path):
    cell_w, cell_h, thumb_w, thumb_h = 420, 300, 390, 185
    cols = 2
    canvas = Image.new("RGB", (cols * cell_w, max(1, (len(rows) + cols - 1) // cols) * cell_h), "white")
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except OSError:
        font = ImageFont.load_default()
    for index, row in enumerate(rows):
        x, y = (index % cols) * cell_w, (index // cols) * cell_h
        draw.rectangle((x + 5, y + 5, x + cell_w - 5, y + cell_h - 5), outline="gray", width=2)
        draw.text((x + 16, y + 12), f"Scene {row['scene']}: {' '.join(row['text'].split()[:6])}", fill="black", font=font)
        paths = row["images"]
        if not paths:
            draw.text((x + 16, y + 65), "NO MATCHED IMAGE", fill="red", font=font)
        else:
            try:
                with Image.open(paths[0]) as original:
                    thumb = original.convert("RGB")
                    thumb.thumbnail((thumb_w, thumb_h))
                    canvas.paste(thumb, (x + (cell_w - thumb.width) // 2, y + 45))
                label = paths[0].name if len(paths) == 1 else f"{paths[0].name} (+{len(paths)-1} more)"
                draw.text((x + 16, y + 245), label, fill="black", font=font)
            except OSError:
                draw.text((x + 16, y + 65), f"Cannot preview {paths[0].name}", fill="red", font=font)
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination)
    print(f"MATCH_PREVIEW={destination}")
