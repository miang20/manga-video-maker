"""Free-first editorial polish helpers for the FFmpeg renderer.

Keep effects deterministic and restrained so user-supplied manga, cartoon, and
photographic scenes retain their original style while cuts feel intentional.
"""
import re

_IMPACT_WORDS = re.compile(
    r"\b(crash(?:es|ed)?|suddenly|reveals?|secret|shocking|explodes?|destroy(?:s|ed)?|"
    r"impossible|finally|never|danger|disaster|truth|however|but then|instantly)\b",
    re.IGNORECASE,
)

# FFmpeg xfade transition names supported by modern FFmpeg builds.
_TRANSITIONS = ("fade", "smoothleft", "wipeleft", "fadeblack", "slideright", "smoothright")


def choose_transition(index, previous_text="", current_text=""):
    """Choose a restrained transition based on narrative emphasis and sequence."""
    text = f"{previous_text} {current_text}".strip()
    if _IMPACT_WORDS.search(text):
        return "zoomin" if index % 2 == 0 else "fadeblack"
    if str(previous_text).rstrip().endswith(("?", "!", "…")):
        return "smoothleft" if index % 2 == 0 else "wipeleft"
    return _TRANSITIONS[index % len(_TRANSITIONS)]


def editorial_filter_chain(fps):
    """Subtle contrast, detail and vignette polish without hue-shifting footage."""
    return (
        f"fps={int(fps)},setsar=1,"
        "eq=contrast=1.035:brightness=0.002,"
        "unsharp=5:5:0.25:5:5:0.0,"
        "vignette=PI/5,format=yuv420p"
    )
