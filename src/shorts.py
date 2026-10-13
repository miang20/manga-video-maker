from .utils import run
def make_shorts(source,output,start,end,fps=24,crf=20):
 if start<0 or end<=start:raise ValueError("Shorts range is invalid: start must be non-negative and end must exceed start.")
 output.parent.mkdir(parents=True,exist_ok=True)
 vf=f"scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps={fps},format=yuv420p"
 run(["ffmpeg","-y","-ss",str(start),"-i",source,"-t",str(end-start),"-vf",vf,"-c:v","libx264","-preset","medium","-crf",str(crf),"-c:a","aac","-b:a","192k","-movflags","+faststart",output])
 return output
