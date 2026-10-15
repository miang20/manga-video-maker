import unittest
from PIL import Image, ImageDraw
from src.frame_edges import frame_edge_verdict


class FrameEdgeTests(unittest.TestCase):
    def test_black_background_source_without_bars_passes(self):
        source = Image.new("RGB", (160, 90), "black")
        ImageDraw.Draw(source).rectangle((20, 10, 140, 80), fill="red")
        # Same source after crop/scale; a black edge is part of the artwork.
        frame = source.resize((320, 180))
        result = frame_edge_verdict(frame, source)
        self.assertTrue(result["passed"], result)

    def test_white_background_with_added_black_border_fails(self):
        source = Image.new("RGB", (160, 90), "white")
        frame = source.resize((320, 180))
        draw = ImageDraw.Draw(frame)
        draw.rectangle((0, 0, 319, 3), fill="black")
        draw.rectangle((0, 176, 319, 179), fill="black")
        draw.rectangle((0, 0, 3, 179), fill="black")
        draw.rectangle((316, 0, 319, 179), fill="black")
        result = frame_edge_verdict(frame, source)
        self.assertFalse(result["passed"], result)
        self.assertEqual(set(result["failed_sides"]), {"top", "bottom", "left", "right"})


if __name__ == "__main__":
    unittest.main()
