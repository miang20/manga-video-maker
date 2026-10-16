import os
import shutil
from pathlib import Path
import yaml
name = os.environ["PROJECT_INPUT"]
source = Path("projects") / name
target = Path("projects") / f"{name}-card"
target.mkdir(parents=True, exist_ok=True)
(target / "images").mkdir(parents=True, exist_ok=True)
shutil.copy2(source / "script.txt", target / "script.txt")
shutil.copytree(source / "images", target / "images", dirs_exist_ok=True)
voice = next((source / f"voice{ext}" for ext in (".mp3", ".wav", ".m4a", ".ogg")
              if (source / f"voice{ext}").is_file()), None)
if voice is None:
    raise SystemExit("No voice file found for caption-card render.")
shutil.copy2(voice, target / voice.name)
for music in source.glob('music.*'):
    if music.is_file() and music.suffix.lower() in {'.mp3', '.wav', '.m4a', '.ogg'}:
        shutil.copy2(music, target / music.name)
config = yaml.safe_load(Path("/tmp/config-render.yaml").read_text(encoding="utf-8")) if Path("/tmp/config-render.yaml").is_file() else yaml.safe_load(Path("config.yaml").read_text(encoding="utf-8"))
config["captions"]["caption_mode"] = "card"
Path("/tmp/config-card.yaml").write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
