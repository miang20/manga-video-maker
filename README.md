# Manga Video Maker

## Android quick start (Roman Urdu + English)

1. GitHub par repo open karo: https://github.com/miang20/manga-video-maker
2. `projects/_template` open karo. Copy karne ke liye **Add file → Create new file** se `projects/video-002/script.txt` banao, phir `projects/video-002/images/.gitkeep` aur `projects/video-002/thumbnail/.gitkeep` folders/files bhi banao. Ya template files ko download karke apne project folder mein upload karo.
3. `projects/video-001` (ya apne project) open karo → **Add file → Upload files**. `script.txt`, numbered images (png/jpg/jpeg/webp), aur human narration `voice.mp3` ya `voice.wav` upload karo. Android Chrome mein option na dikhe to **⋮ → Desktop site** use karo.
4. Commit changes to main. Uploading files does not start a render automatically.
5. **Actions → Render Manga Video → Run workflow**, Project field mein folder name (e.g. `video-001`) do. Optional Shorts start/end seconds dono fill karo. **Run workflow** press karo.
6. Green check ke baad run open karo, Artifacts se ZIP download karo. ZIP mein MP4, captions SRT, notes aur thumbnail (agar uploaded ho) honge.

## Project format

- `script.txt`: paragraphs separated by a blank line; each paragraph maps to one image.
- `voice.mp3`, `voice.wav`, `voice.m4a`, or `voice.ogg`: optional uploaded narration. Uploaded voice always takes priority; no TTS runs when it exists.
- `images/`: supported PNG/JPG/JPEG/WebP, naturally sorted (1, 2, 10). Oversized images are optimized in a work cache; originals are not modified. Number of images must match paragraphs.
- `thumbnail/`: optional thumbnail file copied into output.
- `assets/music/`: optional MP3; mixed quietly under narration with sidechain ducking.

Voice files are silence-trimmed, normalized to about -16 LUFS, and resampled to 44.1 kHz. faster-whisper base.en CPU/int8 supplies word timestamps; if transcript alignment is weak, a clear warning is printed and paragraph timing falls back to proportional word counts.

## Outputs

Landscape MP4, SRT captions, notes with duration and paragraph start times, optional copied thumbnail, and optional vertical Shorts MP4. Workflow artifacts are retained for 14 days.
