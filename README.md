# Manga Video Maker

## Android quick start

The Streamlit app is a lightweight front end. Rendering remains in GitHub Actions; Streamlit does not run FFmpeg, Whisper, or CLIP.

## Deploy the app on Streamlit Community Cloud from an Android phone, step by step

1. Open [Streamlit Community Cloud](https://share.streamlit.io/) in Android Chrome and sign in with GitHub.
2. Choose **Create app**, repository `miang20/manga-video-maker`, branch `main`, and main file path `app.py`.
3. Open the app's **Advanced settings / Secrets** before deploying. Add the secret below (replace the placeholder locally; never paste a real token into chat or source code):
   ```toml
   GITHUB_TOKEN = "github_pat_your_fine_grained_token_here"
   ```
4. Deploy the app. If you change files later, use **Manage app → Reboot app** if the change does not appear automatically.
5. Keep the repository public if you want the GitHub Actions workflow to use the free public-repository allowance. Do not put your token in the repository, app code, screenshots, or logs.

## GitHub fine-grained token permissions

Create a fine-grained personal access token scoped to **Only select repositories → miang20/manga-video-maker**. Grant only:

- **Contents: Read and write** — upload and replace files under `projects/<name>/`.
- **Actions: Read and write** — dispatch the render workflow, inspect run status, and download artifacts.
- **Metadata: Read-only** — repository metadata (normally granted automatically).

Set an expiration and revoke the token if it is exposed. Streamlit secrets are server-side; never display or log the token.

## Project format

- `script.txt`: paragraphs separated by a blank line. Optional `IMG: description` hint lines are not spoken or captioned.
- Voice: `voice.mp3`, `voice.wav`, `voice.m4a`, or `voice.ogg`.
- `images/`: PNG/JPG/JPEG/WebP files. With `auto_match: true`, images are matched to scenes using CPU CLIP embeddings. Manual matching uses `match.yaml`.
- Optional music can be uploaded with a project; the existing workflow's music handling is currently based on `assets/music/`, so per-project music routing must be connected before expecting this upload to affect the mix.

## Outputs

The workflow uploads files from `output/*`, including MP4s, SRT, `notes.txt`, and thumbnail when those files are produced. Artifacts are retained for 14 days. Review the `*-match-preview.png` contact sheet and the workflow's match notes before publishing.

## Current front-end integration notes

- The app writes project inputs to `projects/<name>/` on `main` using GitHub's Contents API, then requests a workflow dispatch and polls Actions.
- The app is only a UI; the render job stays in Actions.
- GitHub's Contents API has practical upload limits. The app rejects individual files larger than 25 MB before deleting old project files. GitHub's Contents API may reject some files below that limit too; compress large media before uploading.
- Preview-only runs the CLIP image matcher and uploads the contact-sheet PNG, `match-table.txt`, `notes.txt`, and thumbnail without running voice preparation or rendering steps. Cached model availability and GitHub runner startup affect total time.
- Caption mode/size, music, Shorts, and auto-match settings are passed into the render configuration. These changes still require a manual Actions run to verify end-to-end behavior.
