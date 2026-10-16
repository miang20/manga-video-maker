import re\ndef group_word_boundaries(boundaries, words_per_chunk=3):
    words = [b for b in boundaries if str(b.get("text", "")).strip()]
    n = max(2, min(4, int(words_per_chunk)))
    out = []
    for i in range(0, len(words), n):
        part = words[i:i + n]
        start = max(0.0, float(part[0]["start"]))
        end = float(part[-1]["end"])
        out.append({"start": start, "end": max(start + 0.12, end), "text": " ".join(str(w["text"]).strip() for w in part)})
    return out


def write_ass(captions, path, font_name="Nunito", font_size=76, outline=5, height=1080,
              caption_position="lower_third", box_enabled=True, pop_seconds=0.08,
              smart_director=False):
    """Write timed ASS captions. Smart mode uses per-caption placement and semantic motion."""
    def ts(seconds):
        cs = max(0, int(round(float(seconds) * 100)))
        return f"{cs // 360000}:{(cs // 6000) % 60:02d}:{(cs // 100) % 60:02d}.{cs % 100:02d}"

    center = str(caption_position).lower() == "center"
    alignment = 5 if center else 2
    margin = int(height * (0.50 if center else 0.13))
    border_style = 3 if box_enabled else 1
    back_colour = "&H90000000" if box_enabled else "&HFF000000"
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: {height}
ScaledBorderAndShadow: yes
WrapStyle: 2
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},&H00FFFFFF,&H0000FFFF,&H00000000,{back_colour},-1,0,0,0,100,100,0,0,{border_style},{outline},1,{alignment},70,70,{margin},1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    positions = {
        "top": lambda: (8, 960, max(90, int(height * 0.13))),
        "bottom": lambda: (2, 960, int(height * 0.86)),
        "left": lambda: (4, int(1920 * 0.12), int(height * 0.50)),
        "right": lambda: (6, int(1920 * 0.88), int(height * 0.50)),
    }
    colors = {
        "answer_yes": "&H0064DC32",
        "answer_no": "&H003232FF",
        "question": "&H0000D7FF",
        "fact": "&H0000D7FF",
        "shock": "&H0000D7FF",
        "danger": "&H003232FF",
        "negative": "&H003232FF",
        "positive": "&H0064DC32",
        "emphasis": "&H0000D7FF",
    }
    with open(path, "w", encoding="utf-8") as output:
        output.write(header)
        pop_cs = max(1, int(float(pop_seconds) * 100))
        for caption in captions:
            raw_text = str(caption["text"]).replace("\n", " ")
            text = raw_text.replace("{", r"\{").replace("}", r"\}")
            tags = [f"\\fscx90\\fscy90\\t(0,{pop_cs},\\fscx100\\fscy100)"]
            if smart_director and caption.get("director_position") in positions:
                align, x, y = positions[caption["director_position"]]()
                tags.extend([f"\\an{align}", f"\\pos({x},{y})"])
            kind = str(caption.get("director_kind", "neutral")) if smart_director else "neutral"
            if kind == "answer":
                answer_key = "answer_yes" if re.search(r"\b(yes|correct|exactly|indeed|absolutely)\b", raw_text, re.I) else "answer_no"
                tags.extend([f"\\1c{colors[answer_key]}", "\\bord7", "\\fscx65\\fscy65\\frz-3\\t(0,130,\\fscx112\\fscy112\\frz0)"])
            elif kind == "question":
                tags.extend([f"\\1c{colors[kind]}", "\\fscx78\\fscy78\\frz2\\t(0,130,\\fscx100\\fscy100\\frz0)"])
            elif kind in {"fact", "emphasis"}:
                tags.extend([f"\\1c{colors[kind]}", "\\fscx75\\fscy75\\t(0,120,\\fscx105\\fscy105)\\t(120,190,\\fscx100\\fscy100)"])
            elif kind in {"shock", "danger", "negative", "positive"}:
                tags.extend([f"\\1c{colors[kind]}", "\\fscx80\\fscy80\\frz3\\t(0,65,\\frz-3)\\t(65,130,\\frz0)"])
            animation = "{" + "".join(tags) + "}"
            output.write(f"Dialogue: 0,{ts(caption['start'])},{ts(caption['end'])},Default,,0,0,0,,{animation}{text}\\N\n".replace("\\N\n", "\n"))
