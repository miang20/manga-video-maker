def group_word_boundaries(boundaries,words_per_chunk=3):
 words=[b for b in boundaries if str(b.get("text","")).strip()]; n=max(2,min(4,int(words_per_chunk))); out=[]
 for i in range(0,len(words),n):
  part=words[i:i+n]; start=max(0,float(part[0]["start"])); end=float(part[-1]["end"])
  out.append({"start":start,"end":max(start+.12,end),"text":" ".join(str(w["text"]).strip() for w in part)})
 return out
def write_ass(captions,path,font_name="Nunito",font_size=62,outline=3,height=1080,bottom_fraction=.32):
 def ts(s):
  cs=max(0,int(round(float(s)*100)));return f"{cs//360000}:{(cs//6000)%60:02d}:{(cs//100)%60:02d}.{cs%100:02d}"
 margin=max(35,int(height*bottom_fraction))
 h=f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: {height}
ScaledBorderAndShadow: yes
WrapStyle: 2
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},&H00FFFFFF,&H0000FFFF,&H90000000,&H60000000,1,0,0,0,100,100,0,0,1,{outline},1,2,80,80,{margin},1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
 with open(path,"w",encoding="utf-8") as f:
  f.write(h)
  for c in captions:
   t=str(c["text"]).replace("{",r"\{").replace("}",r"\}").replace("\n"," ")
   f.write(f"Dialogue: 0,{ts(c['start'])},{ts(c['end'])},Default,,0,0,0,,{{\\fad(70,80)\\blur0.3}}{t}\n")
