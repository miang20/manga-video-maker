import unittest
from src.alignment import align_paragraphs


class AlignmentTests(unittest.TestCase):
    def test_fuzzy_word_alignment_preserves_paragraph_order(self):
        paragraphs = ["A lone warrior hears a sound", "The shadow moves across the floor"]
        words = [
            {"text": "A", "start": 0.0, "end": 0.1},
            {"text": "lone", "start": 0.1, "end": 0.3},
            {"text": "warrior", "start": 0.3, "end": 0.6},
            {"text": "hears", "start": 0.6, "end": 0.8},
            {"text": "some", "start": 0.8, "end": 1.0},
            {"text": "sound", "start": 1.0, "end": 1.3},
            {"text": "The", "start": 1.4, "end": 1.5},
            {"text": "shadow", "start": 1.5, "end": 1.8},
            {"text": "moves", "start": 1.8, "end": 2.0},
            {"text": "across", "start": 2.0, "end": 2.3},
            {"text": "the", "start": 2.3, "end": 2.4},
            {"text": "floor", "start": 2.4, "end": 2.8},
        ]
        result = align_paragraphs(paragraphs, words, 2.8)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["start"], 0.0)
        self.assertAlmostEqual(result[-1]["end"], 2.8)
        self.assertAlmostEqual(result[0]["end"], result[1]["start"])
        self.assertLess(result[0]["start"], result[0]["end"])
        self.assertLess(result[1]["start"], result[1]["end"])

    def test_cumulative_word_count_fallback(self):
        paragraphs = ["A completely different phrase", "Another unrelated sentence"]
        words = [
            {"text": "utterly", "start": 0.0, "end": 0.3},
            {"text": "unknown", "start": 0.3, "end": 0.7},
            {"text": "speech", "start": 0.7, "end": 1.1},
            {"text": "is", "start": 1.1, "end": 1.2},
            {"text": "here", "start": 1.2, "end": 1.6},
        ]
        result = align_paragraphs(paragraphs, words, 1.6)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["start"], 0.0)
        self.assertAlmostEqual(result[-1]["end"], 1.6)
        self.assertLessEqual(result[0]["end"], result[1]["start"] + 1e-6)


if __name__ == "__main__":
    unittest.main()
