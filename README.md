# Manga Video Maker

## Android quick start

1. **Custom video (optional):** open [projects/video-001](https://github.com/miang20/manga-video-maker/tree/main/projects/video-001), upload `script.txt`, images in any order with any filenames, and optionally `voice.mp3` (WAV, M4A, and OGG are also accepted). Add an optional `IMG: short picture description` line under each paragraph.
2. Open **Actions → Render Manga Video → Run workflow**. Keep the defaults (`video-001`) and press **Run workflow**. If no voice file exists, the workflow generates offline test narration with 1.5 seconds of leading silence, a quiet music pad, manga-style placeholder images, and a thumbnail. Edge TTS is not used.
3. Wait for the run to finish, open it, and download the **manga-video-video-001** artifact ZIP. Check the `*-match-preview.png` contact sheet, then review the MP4s, SRT captions, `notes.txt`, and thumbnail.

## Project format

- `script.txt`: paragraphs separated by a blank line; add optional `IMG: description` hint lines below paragraphs; hints are not spoken or captioned.
- Optional narration: `voice.mp3`, `voice.wav`, `voice.m4a`, or `voice.ogg`.
- `images/`: PNG/JPG/JPEG/WebP files; with `auto_match: true`, images are matched to scenes using CPU CLIP embeddings. For manual matching, add `match.yaml` mapping scene numbers to image filenames. With `auto_match: false`, numbered filenames retain the legacy order.
- `thumbnail/`: optional image; the sample workflow creates one if missing.
- `assets/music/`: optional MP3. If no music MP3 exists, the workflow creates a quiet synthetic pad and mixes it under narration with sidechain ducking.

## Outputs

The workflow also includes a scene-match table in the logs and `notes.txt`, plus a `*-match-preview.png` contact sheet. upload images in any order, add IMG: hint under each paragraph, run workflow, check the preview sheet.



The workflow uploads every file in `output/*`, including landscape MP4, caption-card MP4, vertical Shorts MP4, SRT captions, `notes.txt`, and thumbnail. A final self-check prints PASS/FAIL for voice silence trimming, 44.1 kHz audio, loudness, music ducking, captions, each MP4, SRT, notes, and thumbnail, followed by a summary table. Artifacts are retained for 14 days.
