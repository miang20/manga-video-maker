import json, os, subprocess
from pathlib import Path
from PIL import Image, ImageDraw
from src.frame_edges import frame_edge_verdict
project = Path('projects') / os.environ['PROJECT_INPUT']
source = None
if os.environ.get('VOICE_SOURCE_INPUT', 'project') == 'kokoro':
    source = project / 'voice.wav'
else:
    source = next((project / ('voice' + ext) for ext in ('.mp3','.wav','.m4a','.ogg')
                   if (project / ('voice' + ext)).is_file()), None)
prepared = project / 'audio' / 'voiceover.wav'
video = Path('output') / (os.environ['PROJECT_INPUT'] + '.mp4')
if not source or not source.is_file() or not prepared.is_file():
    raise SystemExit(f'VOICE_TRIM_CHECK=FAIL; source={source}; prepared={prepared}')
def probe_duration(path):
    return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration',
        '-of','default=noprint_wrappers=1:nokey=1',str(path)], text=True).strip())
def edge_silence(path):
    p = subprocess.run(['ffmpeg','-hide_banner','-i',str(path),'-af',
        'silencedetect=noise=-48dB:d=0.15','-f','null','-'],capture_output=True,text=True)
    import re
    log=p.stderr
    starts=[float(x) for x in re.findall(r'silence_start:\s*([0-9.]+)',log)]
    ends=[float(x) for x in re.findall(r'silence_end:\s*([0-9.]+)',log)]
    total=probe_duration(path); leading=ends[0] if starts and starts[0] <= .05 and ends else (total if starts and starts[0] <= .05 else 0.0)
    trailing=total-starts[-1] if starts and starts[-1] >= (ends[-1] if ends else 0.0) and starts[-1] < total else 0.0
    return min(total,max(0.0,leading)),min(total,max(0.0,trailing))
source_duration, prepared_duration = probe_duration(source), probe_duration(prepared)
leading, trailing = edge_silence(prepared)
removed = source_duration - prepared_duration
print(f'VOICE_TRIM_SOURCE={source}; source_duration={source_duration:.2f}s; prepared_duration={prepared_duration:.2f}s; duration_delta={removed:.2f}s')
print(f'VOICE_TRIM_PREPARED_EDGES=leading {leading:.2f}s; trailing {trailing:.2f}s')
if leading > .30 or trailing > .50:
    raise SystemExit('VOICE_TRIM_CHECK=FAIL; prepared edge silence exceeds 0.30s leading / 0.50s trailing')
print('VOICE_TRIM_CHECK=PASS')
video_duration = probe_duration(video)
delta = abs(video_duration - prepared_duration)
print(f'VIDEO_VOICE_DURATION=video {video_duration:.2f}s; prepared_voice {prepared_duration:.2f}s; difference {delta:.2f}s')
if delta > .7:
    raise SystemExit('VIDEO_VOICE_DURATION_CHECK=FAIL; difference exceeds 0.70s')
print('VIDEO_VOICE_DURATION_CHECK=PASS')
info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','json',str(video)],text=True))
duration=float(info['format']['duration'])
times=[duration*x/7 for x in (1,2,3,4,5,6)]
frames=[]
edge_failures=[]
source_images=sorted([p for p in (project / 'images').iterdir()
                      if p.is_file() and p.suffix.lower() in {'.png','.jpg','.jpeg','.webp'}],
                     key=lambda p: [int(part) if part.isdigit() else part.lower()
                                    for part in __import__('re').split(r'(\\d+)', p.name)])
if not source_images:
    raise SystemExit('FRAME_EDGE_CHECK=FAIL; no source scene images found')
for i,t in enumerate(times,1):
    path=Path('/tmp')/f'frame-preview-{i}.png'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-ss',f'{t:.3f}','-i',str(video),'-frames:v','1','-vf','scale=480:-1',str(path)],check=True)
    image=Image.open(path).convert('RGB')
    # Pair each sample with the source scene at the same relative position in
    # strict filename order; scale/crop that source to the sampled frame size.
    source_path=source_images[min(len(source_images)-1, int((t / max(duration, 0.001))*len(source_images)))]
    source_image=Image.open(source_path).convert('RGB')
    verdict=frame_edge_verdict(image, source_image, strip_px=4)
    if i <= 3:
        print(f"FRAME_EDGE_SAMPLE={i} source={source_path.name} frame_edges={verdict['frame_edges']} source_edges={verdict['source_edges']} verdict={'PASS' if verdict['passed'] else 'FAIL'}")
    edge_failures.extend(f"sample {i} {side}: frame black edge absent from source" for side in verdict['failed_sides'])
    frames.append(image)
tile_w,tile_h=480,frames[0].height
sheet=Image.new('RGB',(tile_w*3,(tile_h+28)*2),'white')
draw=ImageDraw.Draw(sheet)
for i,im in enumerate(frames):
    x=(i%3)*tile_w; y=(i//3)*(tile_h+28)
    sheet.paste(im,(x,y+28)); draw.text((x+8,y+7),f'Frame {i+1} @ {times[i]:.1f}s',fill='black')
Path('output').mkdir(exist_ok=True)
sheet.save('output/frames-preview.png')
print('FRAME_PREVIEW=output/frames-preview.png')
edge_report = 'FRAME_EDGE_CHECK=FAIL; ' + '; '.join(edge_failures) if edge_failures else 'FRAME_EDGE_CHECK=PASS; sampled 6 frames; source-aware edge comparison'
Path('/tmp/frame-edge-check.txt').write_text(edge_report + '\n', encoding='utf-8')
print(edge_report)
if edge_failures:
    raise SystemExit('FRAME_EDGE_CHECK=FAIL; ' + '; '.join(edge_failures))
print('FRAME_EDGE_CHECK=PASS; sampled 6 frames; no black edge bars detected')
