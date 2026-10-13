import math
from PIL import Image,ImageDraw,ImageFont
from .utils import run
def render_still(image,output,duration,width,height,fps,zoom,direction,grain=True,grain_opacity=.1):
 frames=max(1,math.ceil(duration*fps));delta=max(1,float(zoom))-1
 z=f"min(1+{delta:.6f}*on/{frames},{zoom:.6f})" if direction=="in" else f"max({zoom:.6f}-{delta:.6f}*on/{frames},1.0)"
 vf=[f"scale={width}:{height}:force_original_aspect_ratio=decrease",f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black",f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={width}x{height}:fps={fps}","setsar=1","format=yuv420p"]
 if grain:vf.append(f"noise=alls={max(1,int(grain_opacity*30))}:allf=t+u")
 run(["ffmpeg","-y","-loop","1","-i",image,"-vf",",".join(vf),"-t",f"{duration:.4f}","-r",fps,"-an","-c:v","libx264","-preset","ultrafast","-crf","22",output])
def text_card(text,output,duration,width,height,fps,font):
 im=Image.new("RGB",(width,height),"black");d=ImageDraw.Draw(im)
 try:f=ImageFont.truetype(str(font),72)
 except OSError:f=ImageFont.load_default()
 lines=[];cur=""
 for word in text.split():
  candidate=(cur+" "+word).strip()
  if d.textbbox((0,0),candidate,font=f)[2]>width-180 and cur:lines.append(cur);cur=word
  else:cur=candidate
 if cur:lines.append(cur)
 boxes=[d.textbbox((0,0),s,font=f) for s in lines]; total=sum(b[3]-b[1] for b in boxes)+20*max(0,len(boxes)-1);y=(height-total)//2
 for s,b in zip(lines,boxes):
  d.text(((width-(b[2]-b[0]))//2,y),s,font=f,fill="white",stroke_width=1,stroke_fill=(30,30,30));y+=b[3]-b[1]+20
 still=output.with_suffix(".png");im.save(still)
 try:render_still(still,output,duration,width,height,fps,1.0,"in",True,.08)
 finally:still.unlink(missing_ok=True)
