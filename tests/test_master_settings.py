import json
import tempfile
import unittest
from pathlib import Path
from src.project_settings import resolve_project_settings
from src.kokoro_voice import ENGLISH_VOICES

class MasterSettingsTests(unittest.TestCase):
    def test_missing_and_partial_project_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            self.assertEqual(resolve_project_settings(root)['style'],'bw_manga')
            (root/'project.json').write_text(json.dumps({'style':'color'}))
            got=resolve_project_settings(root)
            self.assertEqual(got['style'],'color')
            self.assertEqual(got['voice_source'],'upload')
    def test_workflow_overrides_win(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'project.json').write_text(json.dumps({'style':'bw_manga'}))
            self.assertEqual(resolve_project_settings(root,{'style':'color'})['style'],'color')
    def test_default_kokoro_voice_is_supported(self):
        self.assertIn('af_heart',ENGLISH_VOICES)

if __name__=='__main__': unittest.main()
