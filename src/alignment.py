from __future__ import annotations
import difflib
import re

def _tokens(text: str) -> list[str]:
    return [t.lower().replace("’", "'") for t in re.findall(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)*", text)]

def align_paragraphs(paragraphs: list[str], words: list[dict], audio_duration: float) -> list[dict]:
    """Fuzzy-align script paragraphs to ASR words, falling back to cumulative word counts.

Acceptance-test trigger: Run voice-file acceptance test."""
    if not paragraphs:
        return []
    if not words:
        raise ValueError("Cannot align paragraphs: transcription contains no words.")
    audio_flat = []
    for word in words:
        found = _tokens(str(word.get("text", "")))
        audio_flat.append(found[0] if found else "")
    paragraph_tokens = [_tokens(p) for p in paragraphs]
    flat_script = [token for part in paragraph_tokens for token in part]
    if not flat_script:
        raise ValueError("Cannot align an empty script.")
    mapping = {}
    for a, b, size in difflib.SequenceMatcher(a=flat_script, b=audio_flat, autojunk=False).get_matching_blocks():
        for offset in range(size):
            mapping[a + offset] = b + offset
    total_words = max(1, len(flat_script))
    duration = max(float(audio_duration), float(words[-1]["end"]), 0.01)
    results = []
    script_cursor = 0
    cumulative = 0
    for tokens in paragraph_tokens:
        count = len(tokens)
        indexes = [mapping[i] for i in range(script_cursor, script_cursor + count) if i in mapping]
        expected_start = cumulative / total_words * duration
        expected_end = (cumulative + count) / total_words * duration
        if indexes:
            start_i, end_i = min(indexes), max(indexes)
            if abs(float(words[start_i]["start"]) - expected_start) > max(8.0, duration * .25):
                start_i = min(range(len(words)), key=lambda i: abs(float(words[i]["start"]) - expected_start))
            if abs(float(words[end_i]["end"]) - expected_end) > max(8.0, duration * .25):
                end_i = min(range(len(words)), key=lambda i: abs(float(words[i]["end"]) - expected_end))
        else:
            start_i = min(range(len(words)), key=lambda i: abs(float(words[i]["start"]) - expected_start))
            end_i = min(range(len(words)), key=lambda i: abs(float(words[i]["end"]) - expected_end))
        end_i = max(start_i, end_i)
        start = float(words[start_i]["start"]) if indexes else expected_start
        end = float(words[end_i]["end"]) if indexes else expected_end
        if results:
            start = max(start, results[-1]["end"])
        start = max(0.0, min(start, duration - .01))
        end = max(start + .05, min(end, duration))
        results.append({"start": start, "end": end, "word_start_index": start_i, "word_end_index": end_i + 1})
        script_cursor += count
        cumulative += count
    results[0]["start"] = 0.0
    results[-1]["end"] = duration
    for i in range(1, len(results)):
        boundary = (results[i - 1]["end"] + results[i]["start"]) / 2
        results[i - 1]["end"] = boundary
        results[i]["start"] = boundary
    return results
