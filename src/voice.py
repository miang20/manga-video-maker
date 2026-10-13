from __future__ import annotations
import shutil
import subprocess
import re
from pathlib import Path
from faster_whisper import WhisperModel
from .utils import run

VOICE_EXTENSIONS = (".mp3", ".wav", ".m4a", ".ogg")

def find_voice_file(project: Path) -> Path | None:
    for ext in VOICE_EXTENSIONS:
        candidate = project / ("voice" + ext)
        if candidate.is_file() and candidate.stat().st_size:
            return candidate
    return None

def _audio_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        check=True, capture_output=True, text=True,
    )
    return max(0.0, float(result.stdout.strip() or 0.0))


def _edge_silence(source: Path, threshold_db: float, min_silence: float, total: float) -> tuple[float, float]:
    """Measure only silence touching the beginning or end; internal pauses are ignored."""
    probe = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(source), "-af",
         f"silencedetect=noise={threshold_db}dB:d={min_silence}", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    log = probe.stderr
    starts = [float(value) for value in re.findall(r"silence_start:\s*([0-9.]+)", log)]
    ends = [float(value) for value in re.findall(r"silence_end:\s*([0-9.]+)", log)]

    leading = 0.0
    if starts and starts[0] <= 0.05:
        # A leading silence normally has a matching silence_end. If the whole
        # recording is silent, cap the report to the full source duration.
        leading = ends[0] if ends else total

    trailing = 0.0
    # FFmpeg does not emit silence_end when silence continues to EOF. Therefore
    # detect a final silence_start that occurs after the last completed silence.
    last_completed_end = ends[-1] if ends else 0.0
    if starts and starts[-1] >= last_completed_end and starts[-1] < total:
        trailing = total - starts[-1]

    return max(0.0, min(total, leading)), max(0.0, min(total, trailing))


def prepare_voice(source: Path, target: Path, config: dict) -> None:
    audio = config.get("audio", {})
    silence = float(audio.get("silence_threshold_db", -48))
    min_silence = float(audio.get("silence_min_seconds", .15))
    sample_rate = int(audio.get("sample_rate", 44100))
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.stem + ".edge-trim.wav")
    original_duration = _audio_duration(source)
    removed_start, removed_end = _edge_silence(source, silence, min_silence, original_duration)
    # Reverse-and-trim ensures only the two outer edges are removed.
    edge_filter = (
        f"silenceremove=start_periods=1:start_duration={min_silence}:start_threshold={silence}dB,"
        "areverse,"
        f"silenceremove=start_periods=1:start_duration={min_silence}:start_threshold={silence}dB,"
        "areverse"
    )
    try:
        run(["ffmpeg", "-y", "-i", source, "-af", edge_filter,
             "-ar", str(sample_rate), "-ac", "2", "-c:a", "pcm_s16le", temporary])
        trimmed_duration = _audio_duration(temporary)
        run(["ffmpeg", "-y", "-i", temporary, "-af",
             f"loudnorm=I={float(audio.get('target_lufs', -16))}:TP={float(audio.get('true_peak_db', -1.5))}:LRA={float(audio.get('lra', 11))},aresample={sample_rate}",
             "-ar", str(sample_rate), "-ac", "2", "-c:a", "pcm_s16le", target])
    finally:
        temporary.unlink(missing_ok=True)
    print(f"VOICE_TRIM_START removed={removed_start:.2f}s")
    print(f"VOICE_TRIM_END removed={removed_end:.2f}s")
    print(
        f"VOICE_TRIM_DURATION original={original_duration:.2f}s; trimmed={trimmed_duration:.2f}s; "
        f"removed_total={max(0.0, original_duration - trimmed_duration):.2f}s"
    )


def synthesize(text: str, path: Path, config: dict) -> list[dict]:
    """Generate offline narration; never call a network TTS service."""
    if not shutil.which("espeak-ng"):
        raise RuntimeError("Offline narration requires espeak-ng.")
    wav_path = path.with_suffix(".offline.wav")
    speed = int(config.get("voice", {}).get("offline_speed", 145))
    subprocess.run(["espeak-ng", "-v", "en-us", "-s", str(speed), "-w", str(wav_path), text],
                   check=True, capture_output=True, text=True)
    try:
        run(["ffmpeg", "-y", "-i", wav_path, "-codec:a", "libmp3lame", "-b:a", "96k", path])
    finally:
        wav_path.unlink(missing_ok=True)
    words, _ = transcribe_word_timestamps(path, config.get("transcription", {}))
    return words

def transcribe_word_timestamps(audio_path: Path,config: dict)->tuple[list[dict],float]:
    c=config.get("transcription",{}); model=WhisperModel(str(c.get("model","base.en")),device="cpu",compute_type="int8",download_root=str(Path(c["model_cache"]).expanduser()) if c.get("model_cache") else None)
    segments,info=model.transcribe(str(audio_path),word_timestamps=True,vad_filter=False,beam_size=int(c.get("beam_size",5)))
    words=[]
    for segment in segments:
        for word in segment.words or []:
            token=(word.word or "").strip()
            if token: words.append({"text":token,"start":max(0.,float(word.start)),"end":max(float(word.start)+.01,float(word.end))})
    if not words: raise RuntimeError(f"faster-whisper returned no word timestamps for {audio_path}. Check that the voice file contains audible speech.")
    return words,float(getattr(info,"duration",0.) or words[-1]["end"])
