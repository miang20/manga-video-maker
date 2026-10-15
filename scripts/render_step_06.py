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
make_shorts(source, target, float(os.environ["SHORTS_START"]), float(os.environ["SHORTS_END"]),
            int(cfg.get("video", {}).get("fps", 24)), int(cfg.get("video", {}).get("crf", 20)))
print(f"SHORTS_OK={target}")
      - name: Verify MP4 streams and duration
        if: ${{ !inputs.preview_only }}
        id: verify_outputs
        run: |
python - <<'PY'
import json, subprocess
from pathlib import Path
videos = list(Path("output").glob("*.mp4"))
if not videos: raise SystemExit("No MP4 output found.")
for video in videos:
    probe = json.loads(subprocess.check_output(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(video)]))
    streams = probe.get("streams", [])
    if not any(s.get("codec_type") == "video" for s in streams): raise SystemExit(f"{video} has no video stream")
    audio = [s for s in streams if s.get("codec_type") == "audio"]
    if not audio: raise SystemExit(f"{video} has no audio stream")
    print(f"VERIFIED {video}: {probe['format'].get('duration')} sec, audio={audio[0].get('codec_name')}, sample_rate={audio[0].get('sample_rate')}")
