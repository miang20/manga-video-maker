# Master Video Maker

General-purpose renderer for any niche and any uploaded scene-image style. The narration is never rewritten and images are never smart-picked: numbered files are used in strict natural filename order.

## Android: start a new project in 3 steps

1. Create a folder under `projects/<project-name>/` with `script.txt` and an `images/` folder.
2. Upload your exact script and numbered scene images (`01.png`, `02.jpg`, `03.webp`, etc.). Add `voice.wav` (or another supported `voice.*`) for upload voice. Voice upload is optional in Kokoro mode.
3. Open GitHub → Actions → Render Video → Run workflow, enter the project folder name and settings, then download the MP4 and companion files from the workflow artifact.

## Acceptance check

Acceptance check: Actions -> Acceptance -> Run workflow -> read the Summary at the top.

## Project files

- `script.txt`: spoken paragraphs separated by a blank line; script text is preserved.
- `images/`: PNG, JPG, JPEG, or WebP; exactly one image per image paragraph, strict natural filename order.
- `voice.mp3`, `voice.wav`, `voice.m4a`, or `voice.ogg`: optional when `voice_source` is `kokoro`.
- `music.*`: optional background music.
- `project.json`: optional object; all fields are optional.

Example optional settings:

```json
{
  "voice_source": "upload",
  "voice": "af_heart",
  "voice_speed": 1.0,
  "style": "bw_manga",
  "motion_intensity": "normal",
  "music": "on"
}
```

## Styles

- `bw_manga`: default legacy grain/look settings.
- `color`: preserves uploaded RGB colors and uses very light grain.
- `clean`: disables grain.

To add a style, copy a JSON file in `config/styles/`, rename it, and edit its settings. Select it in the project settings or manual workflow. Captions are rendered independently of image style.

## Voice

`upload` keeps the existing uploaded voice workflow. `kokoro` generates English narration from the script using the selected Kokoro English voice, sentence/paragraph pauses, and normalized pipeline audio. Kokoro dependencies are installed only when Kokoro is selected. Failure stops the render with an explicit error; there is no silent voice fallback.

## Outputs and compatibility

The manual-only GitHub Actions workflow publishes landscape MP4, vertical Shorts MP4, SRT, notes, and thumbnail. Existing caption word timing/appearance and music sidechain ducking are retained. Default settings are intended to preserve existing output behavior.

## Streamlit

Deploy `app.py` to Streamlit Community Cloud and set `GITHUB_TOKEN` in app Secrets. Give the token only Contents read/write and Actions read/write permissions. The app uploads project files and dispatches the manual workflow; rendering runs in GitHub Actions. Never put the token in source code or chat.
