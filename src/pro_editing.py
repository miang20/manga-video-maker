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


def transition_sfx_graph(scene_intervals, duration, sample_rate=44100):
    """Build quiet, synthetic transition whooshes without external assets or APIs.

    The effect track is mixed under narration and music. Very short videos or
    single-scene projects simply return an empty graph.
    """
    duration = max(0.0, float(duration))
    events = []
    for start, _end in list(scene_intervals)[1:]:
        at = max(0.0, float(start))
        if 0.12 < at < duration - 0.28:
            events.append(at)
    if not events:
        return ""

    filters = []
    labels = []
    for index, at in enumerate(events):
        label = f"whoosh{index}"
        delay_ms = int(round(at * 1000))
        filters.append(
            f"anoisesrc=color=white:sample_rate={int(sample_rate)}:channels=2:"
            f"duration=0.32:amplitude=0.12,"
            "highpass=f=700,lowpass=f=6000,"
            "afade=t=in:st=0:d=0.035,afade=t=out:st=0.07:d=0.25,"
            f"volume=0.5,adelay={delay_ms}|{delay_ms}[{label}]"
        )
        labels.append(f"[{label}]")
    filters.append(
        "".join(labels)
        + f"amix=inputs={len(labels)}:duration=longest:normalize=0,volume=0.8[sfx_mix]"
    )
    return ";".join(filters)
