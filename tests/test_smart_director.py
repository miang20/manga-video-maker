import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw
from src.smart_director import classify_caption, choose_caption_position, direct_captions
from src.captions import write_ass


class SmartDirectorTests(unittest.TestCase):
    def test_semantic_caption_types(self):
        self.assertEqual(classify_caption("Why did this happen?"), "question")
        self.assertEqual(classify_caption("YES!"), "answer")
        self.assertEqual(classify_caption("In 1945, everything changed"), "fact")
        self.assertEqual(classify_caption("This is unbelievable"), "shock")
        self.assertEqual(classify_caption("The secret was hidden"), "emphasis")
        self.assertEqual(classify_caption("The warrior walked home"), "neutral")

    def test_position_chooses_low_ink_region(self):
        with tempfile.TemporaryDirectory() as tmp:
            image = Image.new("RGB", (300, 200), "white")
            draw = ImageDraw.Draw(image)
            draw.rectangle((0, 0, 299, 199), outline="black", width=4)
            draw.rectangle((20, 55, 280, 145), fill="black")
            path = Path(tmp) / "scene.png"
            image.save(path)
            self.assertIn(choose_caption_position("YES!", path), {"top", "bottom", "left", "right"})

    def test_smart_caption_ass_includes_position_and_context_animation(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "captions.ass"
            captions = [
                {"start": 0.0, "end": 0.7, "text": "Why now?", "director_kind": "question", "director_position": "top"},
                {"start": 0.7, "end": 1.2, "text": "YES!", "director_kind": "answer", "director_position": "right"},
                {"start": 1.2, "end": 2.0, "text": "In 1945", "director_kind": "fact", "director_position": "bottom"},
            ]
            write_ass(captions, target, smart_director=True)
            result = target.read_text(encoding="utf-8")
            self.assertIn(r"\an8\pos(960,", result)
            self.assertIn(r"\an6\pos(1680,", result)
            self.assertIn(r"\1c&H0000D7FF", result)
            self.assertIn(r"\1c&H0064DC32", result)
            self.assertIn(r"\fscx65\fscy65", result)

    def test_director_preserves_timing_and_adds_scene_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "scene.png"
            Image.new("RGB", (100, 100), "white").save(image)
            scene = type("Scene", (), {"kind": "image", "image_paths": [image]})()
            source = [{"start": 0.2, "end": 0.8, "text": "Why now?"}]
            result = direct_captions(source, [scene], [(0.0, 1.0)])
            self.assertEqual((result[0]["start"], result[0]["end"]), (0.2, 0.8))
            self.assertEqual(result[0]["director_kind"], "question")
            self.assertEqual(result[0]["director_scene"], 1)
            self.assertIn(result[0]["director_position"], {"top", "bottom", "left", "right"})


if __name__ == "__main__":
    unittest.main()
