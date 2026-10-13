def group_word_boundaries(boundaries, words_per_chunk=3):
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
              caption_position="lower_third", box_enabled=True, pop_seconds=0.08):
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
    with open(path, "w", encoding="utf-8") as output:
        output.write(header)
        pop_cs = max(1, int(float(pop_seconds) * 100))
        for caption in captions:
            text = str(caption["text"]).replace("{", r"\{").replace("}", r"\}").replace("\n", " ")
            animation = f"{{\\fscx90\\fscy90\\t(0,{pop_cs},\\fscx100\\fscy100)}}"
            output.write(f"Dialogue: 0,{ts(caption['start'])},{ts(caption['end'])},Default,,0,0,0,,{animation}{text}\n")
