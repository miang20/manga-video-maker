from pathlib import Path
from PIL import Image,ImageDraw
def ensure_sample_images(project):
 folder=project/"images";folder.mkdir(parents=True,exist_ok=True)
 for n in range(1,6):
  path=folder/f"{n:02d}.png"
  if path.exists():continue
  im=Image.new("RGB",(1280,720),"black");d=ImageDraw.Draw(im);x,y=640,360;w=7;white=(245,245,245);gray=(85,85,85)
  d.ellipse((x-52,y-210,x+52,y-106),outline=white,width=w);d.line((x,y-106,x,y+70),fill=white,width=w)
  d.line((x,y-55,x-100,y+5),fill=white,width=w);d.line((x,y-55,x+100,y-5),fill=white,width=w)
  d.line((x,y+70,x-78,y+200),fill=white,width=w);d.line((x,y+70,x+78,y+200),fill=white,width=w)
  if n==1:d.arc((x+125,y-55,x+275,y+85),180,300,fill=gray,width=5)
  elif n==2:d.line((x+140,y-170,x+250,y-210,x+295,y-80),fill=gray,width=5)
  elif n==3:d.line((x-250,y+160,x+250,y+160),fill=gray,width=5)
  elif n==4:d.rectangle((x+150,y-230,x+300,y+180),outline=gray,width=5)
  else:d.ellipse((x-265,y+160,x-205,y+220),outline=white,width=5)
  im.save(path,optimize=True)
