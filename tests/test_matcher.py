from __future__ import annotations
import random
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from src.matcher import match_project
from src.parser import parse_script

class MatcherSelfTest(unittest.TestCase):
    def test_clip_matches_shuffled_labeled_images(self):
        labels = ["door", "gym", "sleep", "water"]
        paragraphs = [
            "A door creaks open in the dark.",
            "The athlete enters the gym to train.",
            "She falls asleep after a long day.",
            "He drinks fresh water after running.",
        ]
        try:
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                project = root / "project"
                image_dir = project / "images"
                image_dir.mkdir(parents=True)
                (project / "script.txt").write_text("\n\n".join(
                    text + "\nIMG: a large clearly labeled " + label + " picture"
                    for text, label in zip(paragraphs, labels)
                ), encoding="utf-8")
                names = ["zebra.png", "alpha.png", "mango.png", "qwerty.png"]
                shuffled = list(zip(labels, names))
                random.Random(17).shuffle(shuffled)
                for label, name in shuffled:
                    image = Image.new("RGB", (640, 420), "white")
                    draw = ImageDraw.Draw(image)
                    try:
                        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 84)
                    except OSError:
                        font = ImageFont.load_default()
                    draw.text((30, 145), label.upper(), fill="black", font=font)
                    image.save(image_dir / name)
                scenes = parse_script(project, image_matches={})
                mapping, rows = match_project(project, scenes, root / "output", {"matcher": {"model": "clip-ViT-B-32"}})
                matched = [mapping[scene.number][0].name if mapping[scene.number] else None for scene in scenes]
                expected = [dict(shuffled)[label] for label in labels]
                self.assertEqual(matched, expected, f"expected {expected}, got {matched}")
                self.assertTrue((root / "output" / "project-match-preview.png").is_file())
        except Exception:
            print("IMAGE_MATCHER_SELF_TEST=FAIL")
            raise
        print("IMAGE_MATCHER_SELF_TEST=PASS")

if __name__ == "__main__":
    unittest.main()
