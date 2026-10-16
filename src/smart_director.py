"""Free, deterministic Smart Caption Director.

Uses narration text/timing plus lightweight image-composition analysis. No paid API,
network request, model download, or script rewrite is required.
"""
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image

YES_NO = re.compile(r"\b(yes|no|absolutely|exactly|never|always|indeed|correct|wrong)\b", re.I)
DATE_NUMBER = re.compile(r"\b(?:\d{1,4}(?:[,./:-]\d{1,4})*%?|\$\s?\d[\d,.]*|\d+(?:st|nd|rd|th))\b", re.I)
EMOTION = {
    "shock": re.compile(r"\b(shocking|suddenly|unbelievable|impossible|surprisingly|unexpected|astonishing)\b", re.I),
    "danger": re.compile(r"\b(danger|dangerous|deadly|attack|warning|threat|fatal|destroy)\b", re.I),
    "positive": re.compile(r"\b(amazing|incredible|success|won|victory|brilliant|powerful)\b", re.I),
    "negative": re.compile(r"\b(failed|failure|lost|disaster|tragic|terrible|wrong)\b", re.I),
}
STRONG_WORDS = re.compile(r"\b(never|only|first|last|most|every|secret|real|truth|actually|but|because)\b", re.I)


def classify_caption(text: str) -> str:
    """Return a stable visual treatment label based on the spoken caption."""
    value = str(text).strip()
    if not value:
        return "neutral"
    if YES_NO.search(value) and len(value.split()) <= 5:
        return "answer"
    if "?" in value or re.match(r"^(who|what|when|where|why|how|did|does|is|are|can|could|would|will)\b", value, re.I):
        return "question"
    if DATE_NUMBER.search(value):
        return "fact"
    for label, pattern in EMOTION.items():
        if pattern.search(value):
            return label
    if STRONG_WORDS.search(value):
        return "emphasis"
    return "neutral"


def _ink_ratio(image_path: Path, region: tuple[float, float, float, float]) -> float | None:
    """Estimate dark-ink occupancy in a normalized image region; lower is emptier."""
    try:
        with Image.open(image_path) as source:
            image = source.convert("L")
            width, height = image.size
            x1, y1, x2, y2 = region
            crop = image.crop((int(width*x1), int(height*y1), max(int(width*x1)+1, int(width*x2)), max(int(height*y1)+1, int(height*y2))))
            crop.thumbnail((100, 100))
            pixels = list(crop.getdata())
            return sum(1 for p in pixels if p < 105) / max(1, len(pixels))
    except (OSError, ValueError):
        return None


def choose_caption_position(text: str, image_path: str | Path | None = None) -> str:
    """Choose a readable low-ink region; deterministic fallback for missing images."""
    value = str(text).strip()
    if image_path:
        path = Path(image_path)
        # Side captions work best for short phrases; longer text stays horizontally centered.
        regions = {
            "top": (0.08, 0.02, 0.92, 0.27),
            "bottom": (0.08, 0.73, 0.92, 0.98),
        }
        if len(value.split()) <= 3:
            regions["left"] = (0.02, 0.22, 0.27, 0.78)
            regions["right"] = (0.73, 0.22, 0.98, 0.78)
        scores = {name: _ink_ratio(path, region) for name, region in regions.items()}
        available = [(score, name) for name, score in scores.items() if score is not None]
        if available:
            # Prefer a horizontal region when scores are almost tied: it is more legible.
            available.sort(key=lambda item: (item[0], 0 if item[1] in {"top", "bottom"} else 1))
            return available[0][1]
    return "bottom" if len(value.split()) > 3 else "top"


def direct_captions(captions: list[dict], scenes, scene_intervals) -> list[dict]:
    """Attach a scene, visual position, and semantic treatment to each timed caption."""
    output = []
    for original in captions:
        item = dict(original)
        midpoint = (float(item.get("start", 0)) + float(item.get("end", 0))) / 2
        scene_index = next((i for i, (start, end) in enumerate(scene_intervals)
                            if float(start) <= midpoint <= float(end)), len(scene_intervals) - 1)
        scene_index = max(0, scene_index)
        scene = scenes[scene_index] if scenes else None
        image_path = None
        if scene is not None and getattr(scene, "kind", "image") == "image":
            paths = getattr(scene, "image_paths", None) or []
            if paths:
                image_path = paths[0]
        item["director_kind"] = classify_caption(item.get("text", ""))
        item["director_position"] = choose_caption_position(item.get("text", ""), image_path)
        item["director_scene"] = scene_index + 1
        output.append(item)
    return output
