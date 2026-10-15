import math
import random
import hashlib
from PIL import Image, ImageDraw, ImageFont
from .utils import run


def render_still(image, output, duration, width, height, fps, zoom, direction, grain=True,
                 grain_opacity=0.06, max_pan_fraction=0.03, zoom_start=1.0, motion_seed=None):
    frames = max(1, math.ceil(duration * fps))
    zoom_start = max(1.0, float(zoom_start))
    zoom = max(zoom_start, float(zoom))
    delta = zoom - zoom_start
    if direction == "out":
        z = f"max({zoom:.6f}-{delta:.6f}*on/{frames},{zoom_start:.6f})"
    else:
        z = f"min({zoom_start:.6f}+{delta:.6f}*on/{frames},{zoom:.6f})"
    rng = random.Random(str(motion_seed if motion_seed is not None else image))
    pan_x = rng.uniform(-1.0, 1.0) * max(0.0, min(0.03, float(max_pan_fraction)))
    pan_y = rng.uniform(-1.0, 1.0) * max(0.0, min(0.03, float(max_pan_fraction)))
    x = f"max(0,min(iw-iw/zoom,(iw-iw/zoom)/2+({pan_x:.5f})*iw*sin(on/{frames}*PI)))"
    y = f"max(0,min(ih-ih/zoom,(ih-ih/zoom)/2+({pan_y:.5f})*ih*sin(on/{frames}*PI)))"
    vf = [
        f"scale={width}:{height}:force_original_aspect_ratio=increase",
        f"crop={width}:{height}",
        f"zoompan=z='{z}':x='{x}':y='{y}':d=1:s={width}x{height}:fps={fps}",
        "setsar=1", "format=yuv420p"
    ]
    if grain:
        vf.append(f"noise=alls={max(1, int(float(grain_opacity) * 30))}:allf=t+u")
    run(["ffmpeg", "-y", "-loop", "1", "-i", image, "-vf", ",".join(vf), "-t", f"{duration:.4f}",
         "-r", str(fps), "-an", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22", output])


def text_card(text, output, duration, width, height, fps, font, grain=True, grain_opacity=0.06,
              font_size=88, max_pan_fraction=0.03):
    im = Image.new("RGB", (width, height), "black")
    draw = ImageDraw.Draw(im)
    try:
        f = ImageFont.truetype(str(font), int(font_size))
    except OSError:
        f = ImageFont.load_default()
    lines, current = [], ""
    for word in text.split():
        candidate = (current + " " + word).strip()
        if draw.textbbox((0, 0), candidate, font=f)[2] > width - 180 and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    boxes = [draw.textbbox((0, 0), line, font=f, stroke_width=2) for line in lines]
    total = sum(b[3] - b[1] for b in boxes) + 24 * max(0, len(boxes) - 1)
    y = (height - total) // 2
    for line, box in zip(lines, boxes):
        draw.text(((width - (box[2] - box[0])) // 2, y), line, font=f, fill="white",
                  stroke_width=2, stroke_fill="black")
        y += box[3] - box[1] + 24
    still = output.with_suffix(".png")
    im.save(still)
    try:
        render_still(still, output, duration, width, height, fps, 1.0, "in", grain, grain_opacity, 0.0)
    finally:
        still.unlink(missing_ok=True)
