import os
from pathlib import Path

from src.shorts import make_shorts
from src.utils import load_config

name = os.environ["PROJECT_INPUT"]
source = Path("output") / f"{name}.mp4"
target = Path("output") / f"{name}-shorts.mp4"

if not source.is_file():
    raise SystemExit(f"Landscape source is missing: {source}")

cfg = load_config()
make_shorts(
    source,
    target,
    float(os.environ["SHORTS_START"]),
    float(os.environ["SHORTS_END"]),
    int(cfg.get("video", {}).get("fps", 24)),
    int(cfg.get("video", {}).get("crf", 20)),
)
print(f"SHORTS_OK={target}")
