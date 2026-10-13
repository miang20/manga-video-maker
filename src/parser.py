from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import re
@dataclass
class Scene:
 number:int
 text:str
 kind:str="image"
 image_paths:list[Path]|None=None
 music:str|None=None
def _num(name):
 m=re.match(r"^(\d+)[a-zA-Z]?\.(png|jpe?g|webp)$",name,re.I);return int(m.group(1)) if m else None
def _natural(p):return [int(x) if x.isdigit() else x.lower() for x in re.split(r"(\d+)",p.name)]
def parse_script(project_dir:Path):
 script=project_dir/"script.txt"
 if not script.is_file():raise FileNotFoundError(f"Missing script file: {script}")
 raw=script.read_text(encoding="utf-8-sig").replace("\r\n","\n").strip()
 if not raw:raise ValueError(f"Script is empty: {script}")
 blocks=[b.strip() for b in re.split(r"\n\s*\n",raw) if b.strip()]
 folder=project_dir/"images"; imgs=sorted([p for p in folder.glob("*") if p.suffix.lower() in {".png",".jpg",".jpeg",".webp"}],key=_natural) if folder.exists() else []
 scenes=[]; music=None
 for n,block in enumerate(blocks,1):
  lines=[s.strip() for s in block.splitlines() if s.strip()]
  if lines[0].upper().startswith("MUSIC:"):
   music=lines.pop(0).split(":",1)[1].strip()
   if not music:raise ValueError(f"Paragraph {n}: MUSIC: needs a track filename.")
   if not lines:continue
  body="\n".join(lines)
  if body.upper().startswith("CARD:"):
   card=body.split(":",1)[1].strip()
   if not card:raise ValueError(f"Paragraph {n}: CARD: is missing its text.")
   scenes.append(Scene(n,card,"card",[],music));music=None;continue
  found=[p for p in imgs if _num(p.name)==n]
  if not found:raise FileNotFoundError(f"Missing image for paragraph {n}: expected {n:02d}.png (or {n:02d}a.png, {n:02d}b.png, etc.) in {folder}")
  scenes.append(Scene(n,body,"image",found,music));music=None
 if not scenes:raise ValueError("No renderable paragraphs were found in script.txt.")
 return scenes
