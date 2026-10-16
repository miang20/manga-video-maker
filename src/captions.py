from __future__ import annotations

import re


_PUNCTUATION_END = re.compile(r"[.!?…][\"'’”)]*$")
_SOFT_END = re.compile(r"[,;:][\"'’”)]*$")
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "in", "is", "it", "of", "on", "or", "that", "the", "their", "this",
    "to", "was", "were", "with", "you", "your",
}


def group_word_boundaries(boundaries, words_per_chunk=3, min_words_per_chunk=2, max_words_per_chunk=6):
    """Create readable, voice-timed caption beats without rewriting the transcript.

    Sentence punctuation wins; otherwise chunks adapt to speech duration and cadence.
    """
    words = [b for b in boundaries if str(b.get("text", "")).strip()]
    if not words:
        return []

    preferred = max(2, min(6, int(words_per_chunk)))
    minimum = max(1, min(preferred, int(min_words_per_chunk)))
    maximum = max(preferred, min(8, int(max_words_per_chunk)))
    out, current = [], []

    def flush():
        nonlocal current
        if not current:
            return
        start = max(0.0, float(current[0]["start"]))
        end = max(start + 0.12, float(current[-1]["end"]))
        out.append({
            "start": start,
            "end": end,
            "text": " ".join(str(w["text"]).strip() for w in current),
        })
        current = []

    for word in words:
        current.append(word)
        token = str(word.get("text", "")).strip()
        start = float(current[0]["start"])
        end = float(current[-1]["end"])
        count = len(current)
        sentence_end = bool(_PUNCTUATION_END.search(token))
        soft_end = bool(_SOFT_END.search(token))
        too_long = count >= maximum or (end - start) >= 2.25
        punchy_end = count == 1 and (token.isupper() and len(token.strip("!?.,\\"'’”")) >= 3 or "!" in token)
        if (sentence_end and (count >= minimum or punchy_end)) or too_long or (soft_end and count >= minimum):
            flush()
    flush()
    return out


def _caption_layout(index, width, height):
    # Keep the safe area away from the very edge and vary vertical and horizontal
    # placement so captions do not look like a permanently pinned subtitle strip.
    layouts = [
        (8, 0.50, 0.16, 0),   # top centre
        (2, 0.50, 0.82, 0),   # bottom centre
        (6, 0.64, 0.53, 0),   # middle right
        (4, 0.36, 0.56, 0),   # middle left
        (7, 0.39, 0.23, 0),   # upper left
        (9, 0.61, 0.24, 0),   # upper right
        (3, 0.62, 0.79, 0),   # lower right
        (1, 0.38, 0.78, 0),   # lower left
        (5, 0.50, 0.51, 0),   # occasional mid-screen
    ]
    alignment, x, y, angle = layouts[index % len(layouts)]
    return alignment, max(100, min(width - 100, int(width * x))), max(90, min(height - 90, int(height * y))), angle


def _highlight_text(text, base_colour):
    tokens = text.split()
    if not tokens:
        return text
    candidates = [
        (len(re.sub(r"[^A-Za-z0-9']", "", token)), i)
        for i, token in enumerate(tokens)
        if re.sub(r"[^A-Za-z0-9']", "", token).lower() not in _STOPWORDS
        and len(re.sub(r"[^A-Za-z0-9']", "", token)) >= 3
    ]
    if not candidates:
        candidates = [(len(token), i) for i, token in enumerate(tokens)]
    _, highlight_index = max(candidates)
    tokens[highlight_index] = "{\\1c&H000000FF&\\b1}" + tokens[highlight_index] + "{\\1c" + base_colour + "\\b0}"
    return " ".join(tokens)


def write_ass(captions, path, font_name="Nunito", font_size=76, outline=5, height=1080,
              caption_position="lower_third", box_enabled=True, pop_seconds=0.08,
              width=1920, dynamic=True):
    def ts(seconds):
        cs = max(0, int(round(float(seconds) * 100)))
        return f"{cs // 360000}:{(cs // 6000) % 60:02d}:{(cs // 100) % 60:02d}.{cs % 100:02d}"

    # Default fallback keeps the previous lower-third/center behavior if dynamic is off.
    center = str(caption_position).lower() == "center"
    default_alignment = 5 if center else 2
    default_margin = int(height * (0.50 if center else 0.13))
    border_style = 3 if box_enabled else 1
    back_colour = "&H90000000" if box_enabled else "&HFF000000"
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
ScaledBorderAndShadow: yes
WrapStyle: 2
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},&H00FFFFFF,&H000000FF,&H00000000,{back_colour},-1,0,0,0,100,100,0,0,{border_style},{outline},1,{default_alignment},70,70,{default_margin},1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with open(path, "w", encoding="utf-8") as output:
        output.write(header)
        pop_cs = max(1, int(float(pop_seconds) * 100))
        for index, caption in enumerate(captions):
            raw = str(caption["text"]).replace("{", r"\\{").replace("}", r"\\}").replace("\n", " ")
            start = max(0.0, float(caption["start"]))
            end = max(start + 0.12, float(caption["end"]))
            if dynamic:
                alignment, x, y, _ = _caption_layout(index, width, height)
                # Alternate high-contrast monochrome caption plates; red is the only accent.
                white_plate = index % 3 == 2
                base_colour = "&H00000000&" if white_plate else "&H00FFFFFF&"
                plate_colour = "&H00FFFFFF&" if white_plate else "&H00000000&"
                text = _highlight_text(raw, base_colour)
                motion = f"{{\\an{alignment}\\pos({x},{y})\\fad(65,90)\\fscx88\\fscy88\\t(0,{pop_cs},\\fscx100\\fscy100)\\4c{plate_colour}}}"
            else:
                text = raw
                motion = f"{{\\fscx90\\fscy90\\t(0,{pop_cs},\\fscx100\\fscy100)}}"
            output.write(f"Dialogue: 0,{ts(start)},{ts(end)},Default,,0,0,0,,{motion}{text}\n")
