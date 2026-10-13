from pathlib import Path
import re
from PIL import Image
EXTS={".png",".jpg",".jpeg",".webp"}
def natural_key(path):
    return [int(x) if x.isdigit() else x.lower() for x in re.split(r"(\d+)",path.stem)]
def prepare_images(project: Path, scenes):
    folder=project/"images"
    originals=sorted((p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in EXTS),key=natural_key) if folder.exists() else []
    if len(originals)!=len(scenes):
        missing=list(range(min(len(originals),len(scenes))+1,len(scenes)+1))
        extra=list(range(len(scenes)+1,len(originals)+1))
        details=[]
        if missing: details.append("paragraphs with no image: "+", ".join(map(str,missing)))
        if extra: details.append("extra images without paragraphs: "+", ".join(map(str,extra)))
        raise RuntimeError("Image/paragraph count mismatch. "+("; ".join(details) or "Check unsupported or duplicate image files.")+" Add exactly one image per paragraph.")
    cache=project/"work"/"optimized-images"; cache.mkdir(parents=True,exist_ok=True); result=[]
    for i,p in enumerate(originals):
        with Image.open(p) as im:
            im=im.convert("RGB")
            if max(im.size)>1920:
                scale=1920/max(im.size); im=im.resize((max(1,round(im.width*scale)),max(1,round(im.height*scale))),Image.Resampling.LANCZOS)
            out=cache/f"{i+1:04d}.jpg"; im.save(out,"JPEG",quality=92,optimize=True)
        result.append(out)
    return result
