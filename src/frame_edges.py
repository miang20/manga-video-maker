"""Detect black edge bars only when they are absent from the matching source image."""
from __future__ import annotations

from PIL import Image


def _edge_black_ratios(image: Image.Image, strip_px: int = 4) -> dict[str, float]:
    image = image.convert("RGB")
    width, height = image.size
    n = max(1, int(strip_px))
    pixels = image.load()
    strips = {
        "top": [pixels[x, y] for y in range(min(n, height)) for x in range(width)],
        "bottom": [pixels[x, y] for y in range(max(0, height - n), height) for x in range(width)],
        "left": [pixels[x, y] for x in range(min(n, width)) for y in range(height)],
        "right": [pixels[x, y] for x in range(max(0, width - n), width) for y in range(height)],
    }
    return {side: sum(1 for rgb in values if rgb == (0, 0, 0)) / max(1, len(values))
            for side, values in strips.items()}


def frame_edge_verdict(frame: Image.Image, source: Image.Image, strip_px: int = 4,
                       black_threshold: float = 0.97) -> dict:
    """Compare same-position edge strips after source is scaled/cropped to frame geometry.

    Source backgrounds are allowed to be black: a side fails only when the rendered
    frame has an almost entirely pure-black strip while its own processed source does not.
    """
    frame = frame.convert("RGB")
    source = source.convert("RGB")
    width, height = frame.size
    sw, sh = source.size
    scale = max(width / sw, height / sh)
    resized = source.resize((max(width, round(sw * scale)), max(height, round(sh * scale))), Image.Resampling.LANCZOS)
    left = (resized.width - width) // 2
    top = (resized.height - height) // 2
    processed_source = resized.crop((left, top, left + width, top + height))
    frame_edges = _edge_black_ratios(frame, strip_px)
    source_edges = _edge_black_ratios(processed_source, strip_px)
    failed = [side for side in frame_edges
              if frame_edges[side] >= black_threshold and source_edges[side] < black_threshold]
    return {"frame_edges": frame_edges, "source_edges": source_edges,
            "failed_sides": failed, "passed": not failed}
