from __future__ import annotations
import argparse,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT))
from src.parser import parse_script
from src.voice import synthesize
from src.captions import group_word_boundaries,write_ass
from src.effects import render_still,text_card
from src.utils import load_config,ensure_dirs,require_binary,run,ffprobe
from src.shorts import make_shorts
def duration(p):return float(ffprobe(p).get("format",{}).get("duration",0))
def render_project(project,config_path=None):
 project=Path(project).resolve();cfg=load_config(config_path);require_binary("ffmpeg");require_binary("ffprobe")
 if project.name=="video-001":
  from src.sample_assets import ensure_sample_images
  ensure_sample_images(project)
 scenes=parse_script(project);v=cfg.get("video",{});c=cfg.get("captions",{});g=cfg.get("grain",{});m=cfg.get("music",{})
 w=int(v.get("width",1920));h=int(v.get("height",1080));fps=int(v.get("fps",24));pad=float(v.get("scene_padding_seconds",.3));transition=float(v.get("crossfade_seconds",.15))
 work=project/"work";audio=project/"audio";ensure_dirs(work,audio,ROOT/"output")
 candidates=[ROOT/c.get("font","assets/fonts/Nunito-Bold.ttf"),Path(c.get("fallback_font","/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")),Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")]
 font=next((p for p in candidates if p.is_file()),None)
 if font is None:raise FileNotFoundError("No caption font found. Run python setup_fonts.py or install fonts-dejavu-core.")
 clips=[];audios=[];bounds=[];scene_durations=[];offset=0.0
 for scene_index,scene in enumerate(scenes):
  mp3=audio/f"scene-{scene.number:02d}.mp3";local=synthesize(scene.text,mp3,cfg);d=duration(mp3)
  if d<=0:raise RuntimeError(f"Voiceover duration is zero for paragraph {scene.number}.")
  bounds.extend({"text":b["text"],"start":offset+b["start"],"end":offset+b["end"]} for b in local)
  padded=audio/f"scene-{scene.number:02d}-padded.mp3"
  run(["ffmpeg","-y","-i",mp3,"-af",f"apad=pad_dur={pad}","-t",f"{d+pad:.4f}","-c:a","libmp3lame","-q:a","3",padded]);audios.append(padded)
  clip=work/f"scene-{scene.number:02d}.mp4";sd=d+pad;visual_sd=sd+(transition if scene_index<len(scenes)-1 else 0.0);scene_durations.append(sd)
  if scene.kind=="card":text_card(scene.text,clip,visual_sd,w,h,fps,font)
  else:
   paths=scene.image_paths or []
   for image in paths:
    if not image.is_file():raise FileNotFoundError(f"Missing image for paragraph {scene.number}: {image}")
   cross=min(transition,visual_sd/(2*len(paths))) if len(paths)>1 else 0.0
   per=(visual_sd+cross*(len(paths)-1))/len(paths)
   parts=[]
   for j,image in enumerate(paths):
    part=work/f"scene-{scene.number:02d}-part-{j+1:02d}.mp4"
    render_still(image,part,per,w,h,fps,float(v.get("zoom",1.08)),"in" if j%2==0 else "out",bool(g.get("enabled",True)),float(g.get("opacity",.1)));parts.append(part)
   if len(parts)==1:
    run(["ffmpeg","-y","-i",parts[0],"-c","copy",clip])
   else:
    cmd=["ffmpeg","-y"]
    for part in parts:cmd += ["-i",part]
    filters=[f"[{i}:v]settb=AVTB,setpts=PTS-STARTPTS,fps={fps},format=yuv420p[v{i}]" for i in range(len(parts))]
    last="v0"
    for i in range(1,len(parts)):
     nxt=f"x{i}";offset_x=i*(per-cross)
     filters.append(f"[{last}][v{i}]xfade=transition=fade:duration={cross:.4f}:offset={offset_x:.4f}[{nxt}]");last=nxt
    cmd += ["-filter_complex",";".join(filters),"-map",f"[{last}]","-an","-c:v","libx264","-preset","ultrafast","-crf","22",clip]
    run(cmd)
  clips.append(clip);offset+=sd
 al=work/"audio-list.txt";al.write_text("".join("file '"+p.resolve().as_posix()+"'\n" for p in audios),encoding="utf-8")
 voice=audio/"voiceover.mp3";run(["ffmpeg","-y","-f","concat","-safe","0","-i",al,"-c:a","libmp3lame","-q:a","3",voice])
 joined=work/"joined.mp4"
 if len(clips)==1:
  run(["ffmpeg","-y","-i",clips[0],"-c","copy",joined])
 else:
  cmd=["ffmpeg","-y"]
  for clip in clips:cmd += ["-i",clip]
  filters=[f"[{i}:v]settb=AVTB,setpts=PTS-STARTPTS,fps={fps},format=yuv420p[v{i}]" for i in range(len(clips))]
  last="v0";cumulative=0.0
  for i in range(1,len(clips)):
   cumulative+=scene_durations[i-1];nxt=f"scene_x{i}"
   filters.append(f"[{last}][v{i}]xfade=transition=fade:duration={transition:.4f}:offset={cumulative:.4f}[{nxt}]");last=nxt
  cmd += ["-filter_complex",";".join(filters),"-map",f"[{last}]","-an","-c:v","libx264","-preset","ultrafast","-crf","22",joined]
  run(cmd)
 caps=group_word_boundaries(bounds,int(c.get("words_per_chunk",3))) if c.get("enabled",True) else []
 ass=work/"captions.ass"
 if caps:write_ass(caps,ass,"Nunito",int(c.get("size",62)),int(c.get("outline",3)),h,float(c.get("bottom_fraction",.32)))
 music=None
 for scene in scenes:
  if scene.music:
   music=(ROOT/"assets"/"music"/scene.music).resolve()
   if music.parent!=(ROOT/"assets"/"music").resolve() or not music.is_file():raise FileNotFoundError(f"MUSIC track not found in assets/music: {scene.music}")
   break
 if music is None and m.get("enabled",True):music=next((p for p in sorted((ROOT/"assets"/"music").glob("*")) if p.suffix.lower() in {".mp3",".wav",".m4a",".aac"}),None)
 output=ROOT/"output"/f"{project.name}.mp4";vf=f"fps={fps},setsar=1,format=yuv420p"
 if caps:vf+=",ass='"+ass.as_posix().replace(":","\\:")+"'"
 cmd=["ffmpeg","-y","-i",joined,"-i",voice]
 if music:cmd+=["-stream_loop","-1","-i",music]
 cmd+=["-filter_complex"]
 if music:cmd += [f"[1:a]volume=1[voice];[2:a]volume={float(m.get('volume',.055))},afade=t=in:st=0:d={float(m.get('fade_seconds',1.0))}[music];[voice][music]amix=inputs=2:duration=first:dropout_transition=2[aout]"]
 else:cmd += ["[1:a]anull[aout]"]
 cmd += ["-map","0:v:0","-map","[aout]","-vf",vf,"-r",str(fps),"-c:v","libx264","-preset",str(v.get("preset","medium")),"-crf",str(v.get("crf",20)),"-c:a","aac","-b:a","192k","-shortest","-movflags","+faststart",output]
 run(cmd);streams=ffprobe(output).get("streams",[])
 if not any(s.get("codec_type")=="video" for s in streams):raise RuntimeError("Rendered MP4 has no video stream.")
 if not any(s.get("codec_type")=="audio" for s in streams):raise RuntimeError("Rendered MP4 has no audio stream.")
 print(f"RENDER_OK={output}\nDURATION_SECONDS={duration(output):.2f}\nCAPTION_CHUNKS={len(caps)}")
 return output
def main():
 p=argparse.ArgumentParser();p.add_argument("project",nargs="?",default="projects/video-001");p.add_argument("--config");p.add_argument("--shorts-start",type=float);p.add_argument("--shorts-end",type=float);a=p.parse_args()
 try:
  out=render_project(Path(a.project),Path(a.config) if a.config else None)
  if a.shorts_start is not None or a.shorts_end is not None:
   if a.shorts_start is None or a.shorts_end is None:raise ValueError("Provide both --shorts-start and --shorts-end to create Shorts.")
   make_shorts(out,ROOT/"output"/f"{Path(a.project).name}-shorts.mp4",a.shorts_start,a.shorts_end,int(load_config().get("video",{}).get("fps",24)),int(load_config().get("video",{}).get("crf",20)))
 except Exception as e:print(f"RENDER_FAILED: {e}",file=sys.stderr);raise SystemExit(1)
if __name__=="__main__":main()
