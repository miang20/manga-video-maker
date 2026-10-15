import json, os, subprocess, sys
from pathlib import Path
project = Path('projects') / os.environ['PROJECT_INPUT']
settings = {}
config = project / 'project.json'
if config.is_file(): settings = json.loads(config.read_text(encoding='utf-8'))
selected = os.environ.get('VOICE_SOURCE_INPUT', 'project')
if selected != 'project': settings['voice_source'] = selected
if settings.get('voice_source', 'upload') == 'kokoro':
    # Install CPU PyTorch first so Kokoro/Transformers cannot resolve an incompatible build.
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--index-url', 'https://download.pytorch.org/whl/cpu', 'torch==2.6.0+cpu'], check=True)
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'transformers==4.49.0', 'kokoro==0.9.4', 'soundfile'], check=True)
    subprocess.run([sys.executable, '-c', "import importlib.metadata as md, torch, transformers, kokoro; print('TORCH_VERSION=' + torch.__version__); print('TRANSFORMERS_VERSION=' + transformers.__version__); print('KOKORO_VERSION=' + md.version('kokoro')); assert tuple(map(int, torch.__version__.split('+')[0].split('.')[:2])) >= (2, 6), 'PyTorch >=2.6 required'; assert torch.version.cuda is None, 'Expected CPU-only PyTorch'; assert transformers.__version__ == '4.49.0', 'Unexpected Transformers version'; print('KOKORO_IMPORT_CHECK=PASS')"], check=True)
    print('KOKORO_DEPENDENCIES=INSTALLED_AND_VERIFIED')
else:
    print('KOKORO_DEPENDENCIES=SKIPPED; upload/project voice does not install torch')
