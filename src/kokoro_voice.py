from pathlib import Path

ENGLISH_VOICES = ('af_heart','af_alloy','af_aoede','af_bella','af_jessica','af_kore','af_nicole','af_nova','af_river','af_sarah','af_sky','am_adam','am_echo','am_eric','am_fenrir','am_liam','am_michael','am_onyx','am_puck','am_santa','bf_alice','bf_emma','bf_isabella','bf_lily','bm_daniel','bm_fable','bm_george','bm_lewis')
def synthesize_project_voice(project: Path, scenes, voice='af_heart', speed=1.0):
    if voice not in ENGLISH_VOICES:
        raise ValueError('Unsupported Kokoro English voice: ' + str(voice))
    import numpy as np
    import soundfile as sf
    try:
        from kokoro import KPipeline
    except Exception as exc:
        raise RuntimeError('Kokoro dependencies are unavailable; install Kokoro and retry.') from exc
    import re
    pipeline = KPipeline(lang_code='a')
    rate, chunks = 24000, []
    for pi, scene in enumerate(scenes):
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', scene.text.strip()) if s.strip()]
        for si, sentence in enumerate(sentences):
            pieces = []
            try:
                for _, _, audio in pipeline(sentence, voice=voice, speed=float(speed)):
                    if audio is not None:
                        arr = audio.detach().cpu().numpy() if hasattr(audio, 'detach') else np.asarray(audio)
                        pieces.append(np.asarray(arr, dtype=np.float32).reshape(-1))
            except Exception as exc:
                raise RuntimeError('Kokoro failed at paragraph %d sentence %d: %s' % (pi+1, si+1, exc)) from exc
            if not pieces:
                raise RuntimeError('Kokoro produced no audio for paragraph %d sentence %d.' % (pi+1, si+1))
            chunks.append(np.concatenate(pieces))
            chunks.append(np.zeros(int(rate * (0.42 if sentence[-1:] in '.!?' else 0.20)), dtype=np.float32))
        chunks.append(np.zeros(int(rate * 0.55), dtype=np.float32))
    if not chunks:
        raise RuntimeError('No script text available for Kokoro.')
    audio = np.concatenate(chunks)
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak < 0.001:
        raise RuntimeError('Kokoro generated silent narration.')
    if peak > 0.95:
        audio = audio * (0.95 / peak)
    project = Path(project)
    project.mkdir(parents=True, exist_ok=True)
    target = project / 'voice.wav'
    sf.write(str(target), audio, rate, subtype='PCM_16')
    if not target.is_file() or target.stat().st_size < 1000:
        raise RuntimeError('Kokoro voice WAV was not written correctly.')
    return target
