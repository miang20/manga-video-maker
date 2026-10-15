import os
from pathlib import Path
import yaml
config = yaml.safe_load(Path('config.yaml').read_text(encoding='utf-8'))
def enabled(name):
    return os.environ.get(name, 'true').strip().lower() not in {'false', '0', 'no', 'off'}
mode = os.environ.get('CAPTION_MODE_INPUT', 'overlay').strip().lower()
if mode not in {'overlay', 'card'}:
    raise SystemExit('caption_mode must be overlay or card.')
try:
    size = max(40, min(100, int(os.environ.get('CAPTION_SIZE_INPUT', '76'))))
except ValueError:
    raise SystemExit('caption_size must be a number from 40 to 100.')
config.setdefault('captions', {})['caption_mode'] = mode
config['captions']['size'] = size
config['captions']['card_size'] = max(48, int(round(size * 88 / 76)))
config.setdefault('music', {})['enabled'] = enabled('MUSIC_ON_INPUT')
import json
overrides = {}
for env_name, key in [('VOICE_SOURCE_INPUT','voice_source'),('VOICE_INPUT','voice'),('VOICE_SPEED_INPUT','voice_speed'),('STYLE_INPUT','style'),('MOTION_INPUT','motion_intensity')]:
    value = os.environ.get(env_name, 'project')
    if value and value != 'project': overrides[key] = float(value) if key == 'voice_speed' else value
Path('/tmp/settings-overrides.json').write_text(json.dumps(overrides), encoding='utf-8')
Path('/tmp/config-render.yaml').write_text(yaml.safe_dump(config, sort_keys=False), encoding='utf-8')
Path('/tmp/shorts-enabled.txt').write_text('true' if enabled('SHORTS_ON_INPUT') else 'false', encoding='utf-8')
print('RENDER_SETTINGS=' + str({'caption_mode': mode, 'caption_size': size, 'music_on': config['music']['enabled'], 'shorts_on': enabled('SHORTS_ON_INPUT')}))
