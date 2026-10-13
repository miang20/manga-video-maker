from __future__ import annotations
import argparse
import math
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.alignment import align_paragraphs
from src.parser import parse_script
from src.voice import find_voice_file, synthesize, transcribe_word_timestamps
from src.captions import group_word_boundaries, write_ass
from src.effects import render_still, text_card
from src.utils import load_config, ensure_dirs, require_binary, run, ffprobe
from src.shorts import make_shorts


def duration(path):
    return float(ffprobe(path).get("format", {}).get("duration", 0))


def _normalize_words(words, offset=0.0):
    return [{"text": str(w["text"]), "start": float(w["start"]) + offset, "end": float(w["end"]) + offset} for w in words]


def _concat_audio(files, output):
    if len(files) == 1:
        shutil.copy2(files[0], output)
        return
    listing = output.with_suffix(".list.txt")
    listing.write_text("".join("file '" + p.resolve().as_posix().replace("'", "'\\''") + "'\n" for p in files), encoding="utf-8")
    try:
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", listing, "-c:a", "pcm_s16le", "-ar", str(sample_rate), output])
    finally:
        listing.unlink(missing_ok=True)


def render_project(project, config_path=None):
    project = Path(project).resolve()
    cfg = load_config(config_path)
    require_binary("ffmpeg")
    require_binary("ffprobe")
    if project.name == "video-001":
        from src.sample_assets import ensure_sample_images
        ensure_sample_images(project)

    scenes = parse_script(project)
    if not scenes:
        raise RuntimeError("Project has no scenes.")
    video_cfg = cfg.get("video", {})
    caption_cfg = cfg.get("captions", {})
    grain_cfg = cfg.get("grain", {})
    music_cfg = cfg.get("music", {})
    audio_cfg = cfg.get("audio", {})
    sample_rate = int(audio_cfg.get("sample_rate", 44100))
    target_lufs = float(audio_cfg.get("target_lufs", -16))
    true_peak_db = float(audio_cfg.get("true_peak_db", -1.5))
    loudness_range = float(audio_cfg.get("lra", 11))
    transcription_cfg = cfg.get("transcription", {})
    width = int(video_cfg.get("width", 1920))
    height = int(video_cfg.get("height", 1080))
    fps = int(video_cfg.get("fps", 24))
    transition = max(0.0, float(video_cfg.get("crossfade_seconds", 0.15)))
    zoom = float(video_cfg.get("zoom", 1.15))
    max_pan = float(video_cfg.get("max_pan_fraction", 0.03))
    grain_strength = float(grain_cfg.get("strength", 0.06))
    work = project / "work"
    audio_dir = project / "audio"
    ensure_dirs(work, audio_dir, ROOT / "output", ROOT / "assets" / "music")
    candidates = [
        ROOT / caption_cfg.get("font", "assets/fonts/Nunito-Bold.ttf"),
        Path(caption_cfg.get("fallback_font", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]
    font = next((p for p in candidates if p.is_file()), None)
    if font is None:
        raise FileNotFoundError("No caption font found. Run python setup_fonts.py or install fonts-dejavu-core.")

    supplied_voice = find_voice_file(project)
    bounds = []
    scene_intervals = []
    voice_path = audio_dir / "voiceover.wav"
    if supplied_voice:
        print(f"[VOICE] Using uploaded narration file: {supplied_voice.name}; TTS is disabled for this render.")
        shutil.copy2(supplied_voice, voice_path)
        words, transcribed_duration = transcribe_word_timestamps(voice_path, transcription_cfg)
        paragraph_texts = [scene.text for scene in scenes]
        aligned = align_paragraphs(paragraph_texts, words, transcribed_duration)
        for scene, timing in zip(scenes, aligned):
            scene_intervals.append((float(timing["start"]), float(timing["end"])))
        bounds = words
        voice_duration = max(transcribed_duration, duration(voice_path))
    else:
        print("[VOICE] No uploaded voice file found; generating Edge TTS per paragraph.")
        tts_files = []
        cursor = 0.0
        for scene in scenes:
            segment_path = audio_dir / f"scene-{scene.number:02d}.mp3"
            local = synthesize(scene.text, segment_path, cfg)
            segment_duration = duration(segment_path)
            if segment_duration <= 0:
                raise RuntimeError(f"Voiceover duration is zero for paragraph {scene.number}.")
            scene_intervals.append((cursor, cursor + segment_duration))
            bounds.extend(_normalize_words(local, cursor))
            tts_files.append(segment_path)
            cursor += segment_duration
        _concat_audio(tts_files, voice_path)
        voice_duration = duration(voice_path)

    clips = []
    scene_lengths = []
    for scene_index, scene in enumerate(scenes):
        start, end = scene_intervals[scene_index]
        scene_length = max(0.1, end - start)
        scene_lengths.append(scene_length)
        visual_duration = scene_length + (transition if scene_index < len(scenes) - 1 else 0.0)
        clip = work / f"scene-{scene.number:02d}.mp4"
        if scene.kind == "card":
            text_card(scene.text, clip, visual_duration, width, height, fps, font,
                      bool(grain_cfg.get("enabled", True)), grain_strength,
                      int(caption_cfg.get("card_size", 88)), max_pan)
        else:
            images = scene.image_paths or []
            for image in images:
                if not image.is_file():
                    raise FileNotFoundError(f"Missing image for paragraph {scene.number}: {image}")
            if not images:
                raise FileNotFoundError(f"Paragraph {scene.number} has no images.")
            if len(images) == 1:
                render_still(images[0], clip, visual_duration, width, height, fps, zoom,
                             "in" if scene_index % 2 == 0 else "out",
                             bool(grain_cfg.get("enabled", True)), grain_strength, max_pan)
            else:
                per_image = visual_duration / len(images)
                parts = []
                for image_index, image in enumerate(images):
                    part = work / f"scene-{scene.number:02d}-part-{image_index + 1:02d}.mp4"
                    part_duration = per_image + (transition if image_index < len(images) - 1 else 0.0)
                    render_still(image, part, part_duration, width, height, fps, zoom,
                                 "in" if (scene_index + image_index) % 2 == 0 else "out",
                                 bool(grain_cfg.get("enabled", True)), grain_strength, max_pan)
                    parts.append(part)
                cmd = ["ffmpeg", "-y"]
                for part in parts:
                    cmd += ["-i", part]
                filters = [f"[{i}:v]settb=AVTB,setpts=PTS-STARTPTS,fps={fps},format=yuv420p[v{i}]" for i in range(len(parts))]
                last = "v0"
                for i in range(1, len(parts)):
                    nxt = f"image_x{i}"
                    filters.append(f"[{last}][v{i}]xfade=transition=fade:duration={transition:.4f}:offset={i * per_image:.4f}[{nxt}]")
                    last = nxt
                cmd += ["-filter_complex", ";".join(filters), "-map", f"[{last}]", "-an", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22", clip]
                run(cmd)
        clips.append(clip)

    joined = work / "joined.mp4"
    if len(clips) == 1:
        run(["ffmpeg", "-y", "-i", clips[0], "-an", "-c:v", "copy", joined])
    else:
        cmd = ["ffmpeg", "-y"]
        for clip in clips:
            cmd += ["-i", clip]
        filters = [f"[{i}:v]settb=AVTB,setpts=PTS-STARTPTS,fps={fps},format=yuv420p[v{i}]" for i in range(len(clips))]
        last = "v0"
        cumulative = 0.0
        for i in range(1, len(clips)):
            cumulative += scene_lengths[i - 1]
            nxt = f"scene_x{i}"
            filters.append(f"[{last}][v{i}]xfade=transition=fade:duration={transition:.4f}:offset={cumulative:.4f}[{nxt}]")
            last = nxt
        cmd += ["-filter_complex", ";".join(filters), "-map", f"[{last}]", "-an", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22", joined]
        run(cmd)

    caption_mode = str(caption_cfg.get("caption_mode", "overlay")).lower()
    if caption_mode not in {"overlay", "card"}:
        raise ValueError("captions.caption_mode must be 'overlay' or 'card'.")
    caption_chunks = group_word_boundaries(bounds, int(caption_cfg.get("words_per_chunk", 3))) if caption_cfg.get("enabled", True) else []
    ass = work / "captions.ass"
    if caption_chunks:
        is_card_mode = caption_mode == "card"
        write_ass(caption_chunks, ass, "Nunito",
                  int(caption_cfg.get("card_size", 88) if is_card_mode else caption_cfg.get("size", 76)),
                  int(caption_cfg.get("outline", 5)), height,
                  "center" if is_card_mode else str(caption_cfg.get("caption_position", "lower_third")),
                  False if is_card_mode else bool(caption_cfg.get("box_enabled", True)),
                  float(caption_cfg.get("pop_seconds", .08)))
        if is_card_mode:
            black_video = work / "caption-cards-black.mp4"
            run(["ffmpeg", "-y", "-f", "lavfi", "-i",
                 f"color=c=black:s={width}x{height}:r={fps}:d={voice_duration:.4f}",
                 "-an", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22", black_video])
            joined = black_video

    music = None
    for scene in scenes:
        if scene.music:
            music = (ROOT / "assets" / "music" / scene.music).resolve()
            if music.parent != (ROOT / "assets" / "music").resolve() or not music.is_file():
                raise FileNotFoundError(f"MUSIC track not found in assets/music: {scene.music}")
            break
    if music is None and music_cfg.get("enabled", True):
        music = next((p for p in sorted((ROOT / "assets" / "music").glob("*")) if p.suffix.lower() == ".mp3"), None)

    output = ROOT / "output" / f"{project.name}.mp4"
    vf = f"fps={fps},setsar=1,format=yuv420p"
    if caption_chunks:
        vf += ",ass='" + ass.as_posix().replace(":", "\\:").replace("'", "\\'") + "'"
    cmd = ["ffmpeg", "-y", "-i", joined, "-i", voice_path]
    if music:
        cmd += ["-stream_loop", "-1", "-i", music]
    cmd += ["-filter_complex"]
    if music:
        music_linear = math.pow(10.0, float(music_cfg.get("volume_db", -26)) / 20.0)
        threshold = float(music_cfg.get("ducking_threshold", .03))
        ratio = float(music_cfg.get("ducking_ratio", 8))
        fade = float(music_cfg.get("fade_seconds", 1.0))
        cmd += [f"[1:a]aresample={sample_rate},volume=1[voice];[2:a]aresample={sample_rate},volume={music_linear:.6f},afade=t=in:st=0:d={fade},asetpts=PTS-STARTPTS[music];[music][voice]sidechaincompress=threshold={threshold}:ratio={ratio}:attack=20:release=350[ducked];[voice][ducked]amix=inputs=2:duration=first:dropout_transition=2,loudnorm=I={target_lufs}:TP={true_peak_db}:LRA={loudness_range},aresample={sample_rate}[aout]"]
    else:
        cmd += ["[1:a]aresample=44100,loudnorm=I=-16:TP=-1.5:LRA=11,aresample=44100[aout]"]
    cmd += ["-map", "0:v:0", "-map", "[aout]", "-vf", vf, "-r", str(fps),
            "-c:v", "libx264", "-preset", str(video_cfg.get("preset", "medium")),
            "-crf", str(video_cfg.get("crf", 20)), "-c:a", "aac", "-b:a", "192k",
            "-ar", "44100", "-shortest", "-movflags", "+faststart", output]
    run(cmd)
    streams = ffprobe(output).get("streams", [])
    if not any(s.get("codec_type") == "video" for s in streams):
        raise RuntimeError("Rendered MP4 has no video stream.")
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
    if not audio_streams:
        raise RuntimeError("Rendered MP4 has no audio stream.")
    if int(audio_streams[0].get("sample_rate", 0)) != sample_rate:
        raise RuntimeError(f"Expected {sample_rate} Hz final audio, got {audio_streams[0].get('sample_rate')}.")
    print(f"RENDER_OK={output}\nDURATION_SECONDS={duration(output):.2f}\nCAPTION_CHUNKS={len(caption_chunks)}\nVOICE_SOURCE={'uploaded' if supplied_voice else 'edge-tts'}")
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("project", nargs="?", default="projects/video-001")
    parser.add_argument("--config")
    parser.add_argument("--shorts-start", type=float)
    parser.add_argument("--shorts-end", type=float)
    args = parser.parse_args()
    try:
        output = render_project(Path(args.project), Path(args.config) if args.config else None)
        if args.shorts_start is not None or args.shorts_end is not None:
            if args.shorts_start is None or args.shorts_end is None:
                raise ValueError("Provide both --shorts-start and --shorts-end to create Shorts.")
            make_shorts(output, ROOT / "output" / f"{Path(args.project).name}-shorts.mp4",
                        args.shorts_start, args.shorts_end, int(load_config().get("video", {}).get("fps", 24)),
                        int(load_config().get("video", {}).get("crf", 20)))
    except Exception as error:
        print(f"RENDER_FAILED: {error}", file=sys.stderr)
        raise SystemExit(1)

if __name__ == "__main__":
    main()
