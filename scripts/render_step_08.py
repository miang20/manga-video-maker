import os
from pathlib import Path
ordered = [
    ("OUTCOME_CHECKOUT", "Checkout", None),
    ("OUTCOME_SETUP_PYTHON", "Set up Python", None),
    ("OUTCOME_CACHE_WHISPER", "Cache faster-whisper model", None),
    ("OUTCOME_INSTALL_FFMPEG", "Install FFmpeg and fonts", None),
    ("OUTCOME_INSTALL_DEPENDENCIES", "Install dependencies", None),
    ("OUTCOME_INSTALL_FONT", "Install optional Nunito font", None),
    ("OUTCOME_SYNTAX_VALIDATION", "Run syntax and YAML validation", None),
    ("OUTCOME_ALIGNMENT_TESTS", "Run alignment unit tests", None),
    ("OUTCOME_ENSURE_SAMPLE", "Ensure sample project and offline inputs", None),
    ("OUTCOME_RENDER_LANDSCAPE", "Render landscape MP4", "/tmp/render-main.log"),
    ("OUTCOME_RENDER_CARD", "Render caption-card MP4", "/tmp/render-card.log"),
    ("OUTCOME_RENDER_SHORTS", "Render vertical Shorts MP4", None),
    ("OUTCOME_VERIFY_OUTPUTS", "Verify MP4 streams and duration", None),
    ("OUTCOME_MEDIA_QUALITY_CHECKS", "Check voice trimming, duration and preview frames", "/tmp/render-main.log"),
]
failed = next((item for item in ordered if os.environ.get(item[0]) == "failure"), None)
destination = Path("output/first-error.txt")
if failed:
    _, step_name, log_path = failed
    detail = f"Step outcome: failure ({failed[0]})"
    if log_path and Path(log_path).is_file():
        lines = [line.rstrip() for line in Path(log_path).read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]
        if lines:
            detail = "\n".join(lines[-30:])
    message = f"Step: {step_name}\nError:\n{detail}\n"
    if not destination.is_file() or not destination.stat().st_size:
        destination.write_text(message, encoding="utf-8")
    print("FIRST_FAILURE_RECORDED")
    print(destination.read_text(encoding="utf-8"))
else:
    print("FIRST_FAILURE=none before final self-check")
