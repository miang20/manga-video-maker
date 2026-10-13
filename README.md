# Manga Video Maker

## Android quick start

1. **Custom video (optional):** open [projects/video-001](https://github.com/miang20/manga-video-maker/tree/main/projects/video-001) and upload `script.txt`, numbered images, and optionally `voice.mp3` (WAV, M4A, and OGG are also accepted). For the ready-made sample, skip uploads.
2. Open **Actions → Render Manga Video → Run workflow**. Keep the defaults (`video-001`) and press **Run workflow**. If no voice file exists, the workflow generates offline test narration with 1.5 seconds of leading silence, a quiet music pad, manga-style placeholder images, and a thumbnail. Edge TTS is not used.
3. Wait for the run to finish, open it, and download the **manga-video-video-001** artifact ZIP. It contains the MP4s, SRT captions, `notes.txt`, and thumbnail.

## Project format

- `script.txt`: paragraphs separated by a blank line; each paragraph maps to one image.
- Optional narration: `voice.mp3`, `voice.wav`, `voice.m4a`, or `voice.ogg`.
- `images/`: PNG/JPG/JPEG/WebP files, naturally sorted (1, 2, 10). Missing images in the default sample project are generated as simple black-and-white manga placeholders.
- `thumbnail/`: optional image; the sample workflow creates one if missing.
- `assets/music/`: optional MP3. If no music MP3 exists, the workflow creates a quiet synthetic pad and mixes it under narration with sidechain ducking.

## Outputs

The workflow uploads every file in `output/*`, including landscape MP4, caption-card MP4, vertical Shorts MP4, SRT captions, `notes.txt`, and thumbnail. A final self-check prints PASS/FAIL for voice silence trimming, 44.1 kHz audio, loudness, music ducking, captions, each MP4, SRT, notes, and thumbnail, followed by a summary table. Artifacts are retained for 14 days.
