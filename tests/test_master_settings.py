import json
import sys
import tempfile
import types
import unittest
import wave
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image
from src.project_settings import resolve_project_settings
from src.kokoro_voice import ENGLISH_VOICES, synthesize_project_voice
from src.images import prepare_images
from src.effects import render_still
from src.captions import write_ass

class MasterMakerTests(unittest.TestCase):
    def test_missing_and_partial_project_settings_keep_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            self.assertEqual(resolve_project_settings(root)['style'],'bw_manga')
            (root/'project.json').write_text(json.dumps({'style':'color'}))
            got=resolve_project_settings(root)
            self.assertEqual(got['style'],'color')
            self.assertEqual(got['voice_source'],'upload')
            self.assertEqual(got['motion_intensity'],'normal')
            self.assertFalse(got['_motion_explicit'])
    def test_overrides_win_without_changing_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); script=root/'script.txt'; script.write_text('Keep this exact narration.\n')
            (root/'project.json').write_text(json.dumps({'style':'bw_manga'}))
            self.assertEqual(resolve_project_settings(root,{'style':'color'})['style'],'color')
            self.assertEqual(script.read_text(),'Keep this exact narration.\n')
    def test_bw_default_matches_legacy_grain(self):
        preset=json.loads(Path('config/styles/bw_manga.json').read_text())
        self.assertTrue(preset['grain_enabled'])
        self.assertEqual(preset['grain_strength'],0.06)
    def test_color_style_keeps_rgb_pixels(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); folder=root/'images'; folder.mkdir()
            Image.new('RGB',(80,80),(230,20,30)).save(folder/'01.png')
            scene=types.SimpleNamespace(number=1,image_paths=[folder/'01.png'])
            result=prepare_images(root,[scene])[0]
            pixel=Image.open(result).convert('RGB').getpixel((20,20))
            self.assertGreater(pixel[0],200); self.assertLess(pixel[1],50); self.assertLess(pixel[2],60)
    def test_caption_file_is_identical_independent_of_style(self):
        captions=[{'start':0.0,'end':0.8,'text':'Keep captions the same'}]
        with tempfile.TemporaryDirectory() as tmp:
            outputs=[]
            for style in ('bw_manga','color','clean'):
                preset=json.loads(Path('config/styles/'+style+'.json').read_text())
                target=Path(tmp)/(style+'.ass')
                write_ass(captions,target)
                outputs.append(target.read_bytes())
                self.assertNotIn('caption',preset)
            self.assertEqual(outputs[0],outputs[1]); self.assertEqual(outputs[1],outputs[2])
    def test_motion_is_deterministic_and_pan_is_bounded(self):
        with patch('src.effects.run') as mocked:
            render_still('scene.png','out.mp4',1,1920,1080,24,1.15,'in',motion_seed='project:1')
            first=mocked.call_args.args[0]
            render_still('scene.png','out.mp4',1,1920,1080,24,1.15,'in',motion_seed='project:1')
            second=mocked.call_args.args[0]
            self.assertEqual(first,second)
            vf=first[first.index('-vf')+1]
            self.assertIn('max(0,min(iw-iw/zoom',vf)
            self.assertIn('max(0,min(ih-ih/zoom',vf)
    def test_kokoro_writes_expected_voice_file_with_mocked_synthesizer(self):
        fake_kokoro=types.ModuleType('kokoro')
        class Pipeline:
            def __init__(self,lang_code): self.lang_code=lang_code
            def __call__(self,text,voice,speed):
                yield (None,None,np.ones(24000,dtype=np.float32)*0.1)
        fake_kokoro.KPipeline=Pipeline
        fake_soundfile=types.ModuleType('soundfile')
        def fake_write(path,audio,rate,subtype=None):
            samples=(audio.clip(-1,1)*32767).astype(np.int16)
            with wave.open(str(path),'wb') as handle:
                handle.setnchannels(1); handle.setsampwidth(2); handle.setframerate(rate); handle.writeframes(samples.tobytes())
        fake_soundfile.write=fake_write
        with tempfile.TemporaryDirectory() as tmp, patch.dict(sys.modules,{'kokoro':fake_kokoro,'soundfile':fake_soundfile}):
            scene=types.SimpleNamespace(text='Hello, world. Second sentence!')
            output=synthesize_project_voice(Path(tmp),[scene],'af_heart',1.0)
            self.assertEqual(output.name,'voice.wav')
            self.assertGreater(output.stat().st_size,1000)
            with wave.open(str(output),'rb') as handle:
                self.assertEqual(handle.getframerate(),24000)
                self.assertEqual(handle.getnchannels(),1)
                self.assertEqual(handle.getsampwidth(),2)
    def test_default_voice_is_in_supported_english_list(self):
        self.assertIn('af_heart',ENGLISH_VOICES)

if __name__=='__main__': unittest.main()
