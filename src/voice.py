from __future__ import annotations
import asyncio
import time
from pathlib import Path
import edge_tts
from faster_whisper import WhisperModel

def find_voice_file(project: Path) -> Path | None:
    for name in ("voice.mp3", "voice.wav", "voice.m4a"):
        candidate = project / name
        if candidate.is_file() and candidate.stat().st_size > 0:
            return candidate
    return None

async def _edge_tts(text: str, path: Path, voice: str, rate: str, pitch: str) -> list[dict]:
    stream = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch)
    boundaries = []
    with path.open("wb") as output:
        async for item in stream.stream():
            if item["type"] == "audio":
                output.write(item["data"])
            elif item["type"] == "WordBoundary":
                start = float(item.get("offset", 0)) / 10_000_000
                duration = float(item.get("duration", 0)) / 10_000_000
                boundaries.append({"text": item.get("text", ""), "start": start, "end": start + duration})
    if not path.exists() or path.stat().st_size < 1000:
        raise RuntimeError("Edge TTS returned an empty audio file.")
    return boundaries

def synthesize(text: str, path: Path, config: dict) -> list[dict]:
    c = config.get("voice", {})
    voice = c.get("name", "en-US-GuyNeural")
    tries = max(1, int(c.get("retries", 4)))
    error = None
    for attempt in range(tries):
        try:
            return asyncio.run(_edge_tts(text, path, voice, c.get("rate", "+0%"), c.get("pitch", "+0Hz")))
        except Exception as exc:
            error = exc
            path.unlink(missing_ok=True)
            if attempt + 1 < tries:
                time.sleep(float(c.get("retry_delay_seconds", 1.5)) * (attempt + 1))
    raise RuntimeError(f"Voice file missing and Edge TTS is blocked. Upload projects/<project>/voice.mp3. Edge TTS failed after {tries} attempts: {error}") from error

def transcribe_word_timestamps(audio_path: Path, config: dict) -> tuple[list[dict], float]:
    c = config.get("transcription", {})
    model_name = str(c.get("model", "base.en"))
    cache = c.get("model_cache")
    model = WhisperModel(model_name, device="cpu", compute_type="int8", download_root=str(Path(cache).expanduser()) if cache else None)
    segments, info = model.transcribe(str(audio_path), word_timestamps=True, vad_filter=False, beam_size=int(c.get("beam_size", 5)))
    words = []
    for segment in segments:
        for word in segment.words or []:
            token = (word.word or "").strip()
            if token:
                words.append({"text": token, "start": max(0.0, float(word.start)), "end": max(float(word.start) + 0.01, float(word.end))})
    if not words:
        raise RuntimeError(f"faster-whisper returned no word timestamps for {audio_path}. Check that the voice file contains audible speech.")
    return words, float(getattr(info, "duration", 0.0) or words[-1]["end"])
