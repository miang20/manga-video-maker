from pathlib import Path
import re
from PIL import Image

EXTS={".png",".jpg",".jpeg",".webp"}

def natural_key(path):
    return [int(x) if x.isdigit() else x.lower() for x in re.split(r"(\d+)",path.stem)]

def prepare_images(project: Path, scenes):
    """Optimize only images already assigned to scenes, preserving matcher/manual mapping."""
    cache=project/"work"/"optimized-images"
    cache.mkdir(parents=True,exist_ok=True)
    result=[]
    index=0
    for scene in scenes:
        for source in scene.image_paths or []:
            source=Path(source)
            if not source.is_file() or source.suffix.lower() not in EXTS:
                raise FileNotFoundError(f"Matched image does not exist or has an unsupported type: {source}")
            index += 1
            with Image.open(source) as original:
                image=original.convert("RGB")
                if max(image.size)>1920:
                    scale=1920/max(image.size)
                    image=image.resize((max(1,round(image.width*scale)),max(1,round(image.height*scale))),Image.Resampling.LANCZOS)
                output=cache/f"scene-{scene.number:04d}-image-{index:04d}.jpg"
                image.save(output,"JPEG",quality=92,optimize=True)
            result.append(output)
    return result
