import json
import os
import re
import subprocess
from pathlib import Path

name = os.environ["PROJECT_INPUT"]
project = Path("projects") / name
output = Path("output")
results = []
first_error_path = output / "first-error.txt"
first_error_text = first_error_path.read_text(encoding="utf-8", errors="replace").strip() if first_error_path.is_file() else ""
first_step = next((line.split(":", 1)[1].strip() for line in first_error_text.splitlines() if line.startswith("Step:")), "")
if first_error_text:
    print("\nFIRST FAILURE (recorded before summary):")
    print(first_error_text)
else:
    print("\nFIRST FAILURE: none recorded before final self-check")

def check(label, ok, detail):
    status = "PASS" if ok else "FAIL"
    # Once an earlier workflow step failed, downstream self-checks may
    # be unable to run or may only report missing outputs caused by
    # that first failure. Keep the original error authoritative and
    # mark these dependent checks SKIPPED instead of multiplying failures.
    if not ok and first_error_text:
        status = "SKIPPED"
    results.append((label, status, str(detail)))
    print(f"{label}: {status} - {detail}")

def probe(path):
    return json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)
    ], text=True))

voice_source = os.environ.get("VOICE_SOURCE_INPUT", "project")
source_voice = (project / "voice.wav") if voice_source == "kokoro" else next(
    (project / f"voice{ext}" for ext in (".mp3", ".wav", ".m4a", ".ogg")
     if (project / f"voice{ext}").is_file()), None)
prepared_voice = project / "audio" / "voiceover.wav"
trim_ok = False
trim_detail = "correct source or prepared voice file is missing"
if source_voice and source_voice.is_file() and prepared_voice.is_file():
    def duration(path):
        return float(probe(path)["format"].get("duration", 0))
    source_duration = duration(source_voice)
    prepared_duration = duration(prepared_voice)
    edge = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(prepared_voice),
         "-af", "silencedetect=noise=-48dB:d=0.15", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    starts = [float(x) for x in re.findall(r"silence_start:\s*([0-9.]+)", edge.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end:\s*([0-9.]+)", edge.stderr)]
    leading = ends[0] if starts and starts[0] <= 0.05 and ends else (prepared_duration if starts and starts[0] <= 0.05 else 0.0)
    trailing = prepared_duration - starts[-1] if starts and starts[-1] >= (ends[-1] if ends else 0.0) and starts[-1] < prepared_duration else 0.0
    shortened = max(0.0, source_duration - prepared_duration)
    trim_ok = source_duration > 0 and prepared_duration > 0 and leading <= 0.30 and trailing <= 0.50
    trim_detail = (f"source={source_duration:.2f}s; prepared={prepared_duration:.2f}s; "
                   f"shortened={shortened:.2f}s; prepared edge silence leading={leading:.2f}s/trailing={trailing:.2f}s")
check("Voice silence trimmed", trim_ok, trim_detail)

main = output / f"{name}.mp4"
main_ok = main.is_file() and main.stat().st_size > 0
check("Landscape MP4 exists", main_ok, main)
if main_ok:
    main_probe = probe(main)
    videos = [stream for stream in main_probe["streams"] if stream.get("codec_type") == "video"]
    audios = [stream for stream in main_probe["streams"] if stream.get("codec_type") == "audio"]
    landscape = bool(videos and int(videos[0].get("width", 0)) > int(videos[0].get("height", 0)))
    check("Landscape dimensions", landscape, f"{videos[0].get('width')}x{videos[0].get('height')}" if videos else "video stream missing")
    sample_rate_ok = bool(audios and int(audios[0].get("sample_rate", 0)) == 44100)
    check("Final audio 44.1 kHz", sample_rate_ok, audios[0].get("sample_rate") if audios else "audio stream missing")
    measured = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(main), "-af",
         "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    start = measured.stderr.rfind("{")
    end = measured.stderr.find("}", start)
    loudness = None
    if start >= 0 and end > start:
        try:
            loudness = float(json.loads(measured.stderr[start:end + 1]).get("input_i"))
        except (TypeError, ValueError, json.JSONDecodeError):
            loudness = None
    loudness_ok = loudness is not None and abs(loudness - (-16.0)) <= 2.5
    check("Loudness within 2.5 LU of -16 LUFS", loudness_ok,
          f"{loudness:.2f} LUFS" if loudness is not None else "measurement unavailable")
else:
    check("Landscape dimensions", False, "landscape MP4 unavailable")
    check("Final audio 44.1 kHz", False, "landscape MP4 unavailable")
    check("Loudness within 2.5 LU of -16 LUFS", False, "landscape MP4 unavailable")

log = Path("/tmp/render-main.log")
ducking_ran = log.is_file() and "MUSIC_DUCKING=PASS" in log.read_text(encoding="utf-8", errors="replace")
check("Music ducking ran", ducking_ran, "sidechaincompress marker in landscape render log" if ducking_ran else "music ducking marker missing")
edge_report_path = Path("/tmp/frame-edge-check.txt")
edge_report = edge_report_path.read_text(encoding="utf-8", errors="replace").strip() if edge_report_path.is_file() else ""
check("Source-aware frame edge check", "FRAME_EDGE_CHECK=PASS" in edge_report, edge_report or "frame edge report missing")
render_log_text = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
expected_voice = "VOICE_SOURCE_USED=kokoro" if voice_source == "kokoro" else "VOICE_SOURCE_USED=upload"
voice_marker_ok = expected_voice in render_log_text and source_voice is not None and source_voice.is_file()
check("Voice source confirmed", voice_marker_ok, expected_voice + " marker and source file" if voice_marker_ok else "expected voice source marker/file missing")

srt = output / f"{name}.srt"
captions_ok = srt.is_file() and srt.stat().st_size > 0 and any(
    line.strip() and not line.strip().isdigit() and "-->" not in line
    for line in srt.read_text(encoding="utf-8", errors="replace").splitlines()
)
check("Captions present", captions_ok, srt)
card = output / f"{name}-card.mp4"
shorts = output / f"{name}-shorts.mp4"
check("Caption-card MP4 exists", card.is_file() and card.stat().st_size > 0, card)
shorts_enabled = os.environ.get("SHORTS_ON_INPUT", "true").lower() not in {"false", "0", "no", "off"}
check("Shorts MP4 exists", (shorts.is_file() and shorts.stat().st_size > 0) if shorts_enabled else True,
      shorts if shorts_enabled else "Shorts disabled by settings")
check(".srt exists", srt.is_file() and srt.stat().st_size > 0, srt)
notes = output / "notes.txt"
check("notes.txt exists", notes.is_file() and notes.stat().st_size > 0, notes)
thumbnails = sorted(output.glob(f"{name}-thumbnail.*"))
check("Thumbnail exists", bool(thumbnails and thumbnails[0].stat().st_size > 0), thumbnails[0] if thumbnails else "thumbnail missing")

print("\nSUMMARY TABLE")
print("| Check | Result | Detail |")
print("|---|---|---|")
for label, status, detail in results:
    print(f"| {label} | {status} | {detail.replace('|', '/')} |")
markdown = ["| Check | Result | Detail |", "|---|---|---|"]
markdown.extend(f"| {label} | {status} | {str(detail).replace('|', '/')} |" for label, status, detail in results)
(output / "quality-checks.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
failed = [label for label, status, _ in results if status == "FAIL"]
if failed and not first_error_text:
    first_label = failed[0]
    first_error_text = f"Step: Final self-check\nError: {first_label}\n"
    first_error_path.write_text(first_error_text, encoding="utf-8")
    first_step = "Final self-check"
    print("FIRST_FAILURE_RECORDED")
    print(first_error_text)
if first_error_text and not failed:
    failed.append("Earlier workflow step failed: " + first_step)
print(f"SELF_CHECK_SUMMARY={'FAIL' if failed else 'PASS'}")
if failed:
    raise SystemExit("First failure: " + first_step + "; self-check failures: " + ", ".join(failed))
