from __future__ import annotations
import asyncio, time
from pathlib import Path
import edge_tts
from faster_whisper import WhisperModel
from .utils import run

VOICE_EXTENSIONS = (".mp3", ".wav", ".m4a", ".ogg")

def find_voice_file(project: Path) -> Path | None:
    for ext in VOICE_EXTENSIONS:
        candidate = project / ("voice" + ext)
        if candidate.is_file() and candidate.stat().st_size:
            return candidate
    return None

def prepare_voice(source: Path, target: Path, config: dict) -> None:
    audio = config.get("audio", {})
    silence = float(audio.get("silence_threshold_db", -48))
    min_silence = float(audio.get("silence_min_seconds", .15))
    # Detect leading/trailing silence, preserve the interior, convert all supported input codecs.
    run(["ffmpeg","-y","-i",source,"-af",
         f"silenceremove=start_periods=1:start_duration={min_silence}:start_threshold={silence}dB:stop_periods=1:stop_duration={min_silence}:stop_threshold={silence}dB,"
         f"loudnorm=I={float(audio.get('target_lufs',-16))}:TP={float(audio.get('true_peak_db',-1.5))}:LRA={float(audio.get('lra',11))},aresample={int(audio.get('sample_rate',44100))}",
         "-ar",str(int(audio.get("sample_rate",44100))),"-ac","2","-c:a","pcm_s16le",target])

async def _edge_tts(text: str, path: Path, voice: str, rate: str, pitch: str) -> list[dict]:
    stream=edge_tts.Communicate(text,voice=voice,rate=rate,pitch=pitch); boundaries=[]
    with path.open("wb") as out:
        async for item in stream.stream():
            if item["type"]=="audio": out.write(item["data"])
            elif item["type"]=="WordBoundary":
                start=float(item.get("offset",0))/10_000_000; end=start+float(item.get("duration",0))/10_000_000
                boundaries.append({"text":item.get("text",""),"start":start,"end":end})
    if not path.exists() or path.stat().st_size<1000: raise RuntimeError("Edge TTS returned an empty audio file.")
    return boundaries

def synthesize(text: str,path: Path,config: dict)->list[dict]:
    c=config.get("voice",{}); tries=max(1,int(c.get("retries",4))); error=None
    for attempt in range(tries):
        try:return asyncio.run(_edge_tts(text,path,c.get("name","en-US-GuyNeural"),c.get("rate","+0%"),c.get("pitch","+0Hz")))
        except Exception as exc:
            error=exc; path.unlink(missing_ok=True)
            if attempt+1<tries:time.sleep(float(c.get("retry_delay_seconds",1.5))*(attempt+1))
    raise RuntimeError(f"Voice file missing and Edge TTS is blocked. Upload projects/<project>/voice.mp3. Edge TTS failed after {tries} attempts: {error}") from error

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
