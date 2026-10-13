# Manga Video Maker

Free manga-style faceless video builder. GitHub Actions is the recommended Android workflow: upload script/images, run the workflow, download the MP4 artifact.

## Phone workflow
1. Create `projects/video-002/`, then add `script.txt` and an `images/` folder.
2. Write one paragraph per scene, separated by one blank line. Paragraph 1 uses `images/01.png`, paragraph 2 uses `02.png`, etc. PNG/JPG/JPEG/WebP supported. Several images for one paragraph can be named `03a.png`, `03b.png`; their duration is split evenly.
3. In GitHub mobile, open the project folder and use **Add file → Upload files**. Upload images inside `images/`. If upload is hidden, enable **Desktop site** in your browser. Commit to `main`.
4. Open **Actions → Render Manga Video → Run workflow**. Select `main`, enter project folder name only, e.g. `video-002`. Optionally provide both Shorts start/end seconds.
5. When the run turns green, open it and scroll to **Artifacts**. Download `manga-video-video-002` ZIP and extract the MP4. Shorts is included when both range values were supplied. A push under `projects/**` also triggers render.
## Script tags
`CARD: Nobody saw it coming.` creates a black text-card scene and counts as a paragraph. `MUSIC: dark-ambient.mp3` selects a track from `assets/music/` for the next paragraph. Music is optional. Scene duration is narration duration + 0.3s. Captions group 2–4 words using Edge TTS word boundaries.
## Local
Install Python 3.11, FFmpeg, then `pip install -r requirements.txt`, `python setup_fonts.py`, `python render.py projects/video-001`. Output: `output/video-001.mp4`. Shorts: `python render.py projects/video-001 --shorts-start 12 --shorts-end 42`. Optional UI: `streamlit run app.py`.
## Tools and troubleshooting
FFmpeg is free and CPU-only; Edge TTS is a free online service and needs internet. Video is 1920×1080, 24fps H.264/AAC, black-padded slow zoom with grain, 0.15s crossfades between scenes/image variants, and word-timed captions. Vertical export letterboxes the selected landscape range to preserve composition. If script is missing, commit it to the project. “Missing image for paragraph N” means add `images/NN.png` or `NNa.png` etc. If TTS fails, retry workflow; it automatically retries. FFmpeg is installed in Actions. If font download fails, system DejaVu Sans is used. If artifact is missing, wait for the workflow to finish and inspect that run's Artifacts section. Shorts start must be non-negative and end greater than start.
