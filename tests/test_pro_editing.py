import unittest

from src.pro_editing import choose_transition, editorial_filter_chain, transition_sfx_graph


class ProfessionalEditingTests(unittest.TestCase):
    def test_transitions_vary_for_ordinary_scenes(self):
        transitions = [choose_transition(i) for i in range(6)]
        self.assertGreater(len(set(transitions)), 3)

    def test_high_impact_script_beats_get_an_emphasis_transition(self):
        self.assertIn(choose_transition(0, "The room was quiet.", "Suddenly, it explodes!"),
                      {"zoomin", "fadeblack"})


    def test_transition_whooshes_are_free_synthetic_and_voice_timed(self):
        graph = transition_sfx_graph([(0.0, 2.0), (2.0, 4.0), (4.0, 6.0)], 6.0)
        self.assertIn("anoisesrc=", graph)
        self.assertIn("adelay=2000|2000", graph)
        self.assertIn("adelay=4000|4000", graph)
        self.assertIn("[sfx_mix]", graph)

    def test_transition_whooshes_are_skipped_for_single_scene(self):
        self.assertEqual(transition_sfx_graph([(0.0, 5.0)], 5.0), "")

    def test_editorial_grade_keeps_frame_rate_and_monochrome_safe_filters(self):
        chain = editorial_filter_chain(30)
        self.assertIn("fps=30", chain)
        self.assertIn("contrast=1.035", chain)
        self.assertIn("unsharp=", chain)
        self.assertIn("vignette=", chain)
        self.assertNotIn("hue=", chain)


if __name__ == "__main__":
    unittest.main()
