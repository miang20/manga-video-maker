# Manga Video Maker

A free manga-style faceless-video renderer. Recommended Android workflow: upload a script, manga images, and (best quality) your own narration audio; run GitHub Actions and download the MP4 artifact.

## Android phone: upload your own voice.mp3

1. Open https://github.com/miang20/manga-video-maker in Chrome on your Android phone and sign in.
2. Open the project folder, for example projects/video-001. Tap **Add file → Upload files**. If mobile view hides the option, open Chrome menu **⋮ → Desktop site**.
3. Choose your narration recording named exactly voice.mp3 and upload it directly inside the project folder, alongside script.txt. Supported alternatives are voice.wav and voice.m4a; voice.mp3 is checked first.
4. Scroll down, enter a commit message such as “Add human narration”, then tap **Commit changes** to main.
5. Keep script paragraphs in the same order as the spoken recording. The renderer transcribes the voice with faster-whisper base.en on CPU/int8, then aligns paragraphs using fuzzy word matching and cumulative word-count fallback.
6. Open the repository's **Actions** tab → **Render Manga Video** → **Run workflow**. Select branch main, set Project to video-001, then tap **Run workflow**. Wait for the green check.
7. Open the completed run and scroll to **Artifacts**. Download manga-video-video-001, extract the ZIP on your phone, and play video-001.mp4.

Your uploaded voice file takes priority. If it exists, no TTS is called. If no voice file exists, Edge TTS is retried; if still blocked, the job stops with the exact upload instruction instead of switching to a robotic offline voice.

## Project structure

    projects/video-001/
      script.txt
      voice.mp3        # optional but recommended; voice.wav / voice.m4a also work
      images/
        01.png         # paragraph 1 image
        02.png         # paragraph 2 image
        03a.png        # paragraph 3 image variant A
        03b.png        # paragraph 3 image variant B
    assets/music/      # optional background music MP3

Separate paragraphs in script.txt with one blank line. Paragraph 1 uses images/01.png, paragraph 2 uses 02.png, and so on. PNG/JPG/JPEG/WebP are supported. Multiple images with the same paragraph number (e.g. 03a.png and 03b.png) split that paragraph's visual time and crossfade between variants.

- CARD: Nobody saw it coming. creates a full-screen black text-card scene.
- MUSIC: dark-ambient.mp3 selects a track from assets/music/ for the next paragraph.
- If assets/music/ contains an MP3, it is mixed under narration at -26 dB with voice-triggered ducking.
- captions.caption_mode is overlay by default; card mode uses a black-background caption presentation.

## Visual defaults

- 1920×1080, 24 fps H.264/AAC; audio is resampled to 44.1 kHz and loudness-normalized to about -16 LUFS.
- Large 76 px bold white captions with thick black outline, 2–4 words at a time, and a 0.08-second 0.9→1.0 pop-in.
- Captions default to the lower third; caption_position: center centers them. A translucent black caption box can be toggled in config.yaml.
- Alternating visible 1.00→1.15 zoom-in/zoom-out, random pan up to 3% of the frame, subtle grain strength 0.06, and 0.15-second visual crossfades.
- Vertical Shorts export remains available: in workflow inputs, provide both Shorts start and end seconds.

## Acceptance test (temporary test voice)

In **Actions → Render Manga Video → Run workflow**, select video-001 and set **Generate a temporary test voice.wav** to true. The workflow generates a temporary eSpeak test voice.wav on the runner (it is not committed), exercises faster-whisper word alignment and renders the MP4, then uploads the artifact. This is a pipeline test voice, not a substitute for human narration.

## Local run

Install Python 3.11 and FFmpeg, then run:

    python -m pip install -r requirements.txt
    python setup_fonts.py
    python render.py projects/video-001

Output: output/video-001.mp4. Create a Shorts cut with:

    python render.py projects/video-001 --shorts-start 12 --shorts-end 42

Optional UI: streamlit run app.py.

## Troubleshooting

- **Voice file missing and Edge TTS is blocked.** Upload projects/<project>/voice.mp3 and rerun.
- **Missing image for paragraph N:** add images/NN.png or variants such as NNa.png.
- **Model download is slow:** the first faster-whisper run downloads base.en; GitHub Actions caches the Hugging Face model directory for later runs.
- **No artifact:** open that Actions run and inspect the failed step. The workflow checks every output for both video and audio streams.
