import tempfile
import unittest
from pathlib import Path

from src.captions import group_word_boundaries, write_ass


def words(tokens, step=0.35):
    return [
        {"text": token, "start": i * step, "end": i * step + step * 0.8}
        for i, token in enumerate(tokens)
    ]


class CaptionTests(unittest.TestCase):
    def test_sentence_punctuation_closes_a_caption_beat(self):
        result = group_word_boundaries(words(["This", "is", "the", "first", "line.", "Then", "another", "line."]))
        self.assertEqual(result[0]["text"], "This is the first line.")
        self.assertEqual(result[1]["text"], "Then another line.")

    def test_long_speech_is_split_into_readable_timed_chunks(self):
        result = group_word_boundaries(words(["A", "long", "sentence", "without", "punctuation", "keeps", "moving", "through", "the", "scene"]))
        self.assertGreater(len(result), 1)
        self.assertTrue(all(chunk["end"] > chunk["start"] for chunk in result))
        self.assertEqual(" ".join(chunk["text"] for chunk in result).split(),
                         ["A", "long", "sentence", "without", "punctuation", "keeps", "moving", "through", "the", "scene"])

    def test_dynamic_ass_uses_varied_positions_red_highlight_and_monochrome_plates(self):
        captions = [
            {"start": i * 1.0, "end": i * 1.0 + 0.8, "text": text}
            for i, text in enumerate(["This is amazing", "Look at that", "The car explodes"])
        ]
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "captions.ass"
            write_ass(captions, target, width=1920, height=1080)
            content = target.read_text(encoding="utf-8")
        self.assertIn(r"\an8", content)
        self.assertIn(r"\an2", content)
        self.assertIn(r"\pos(", content)
        self.assertIn(r"\fad(", content)
        self.assertIn(r"\1c&H000000FF&", content)
        self.assertIn(r"\4c&H00FFFFFF&", content)
        self.assertIn(r"\4c&H00000000&", content)
        self.assertEqual(content.count("Dialogue:"), 3)

    def test_empty_word_list_returns_no_captions(self):
        self.assertEqual(group_word_boundaries([]), [])


if __name__ == "__main__":
    unittest.main()
