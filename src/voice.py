from __future__ import annotations
import asyncio,time,shutil,subprocess,wave
import edge_tts
async def _synthesize(text,path,voice,rate,pitch):
 stream=edge_tts.Communicate(text,voice=voice,rate=rate,pitch=pitch); bounds=[]
 with path.open("wb") as out:
  async for item in stream.stream():
   if item["type"]=="audio":out.write(item["data"])
   elif item["type"]=="WordBoundary":
    start=float(item.get("offset",0))/10_000_000; d=float(item.get("duration",0))/10_000_000
    bounds.append({"text":item.get("text",""),"start":start,"end":start+d})
 if not path.exists() or path.stat().st_size<1000:raise RuntimeError("Edge TTS returned an empty audio file.")
 return bounds
def synthesize(text,path,config):
 c=config.get("voice",{}); voice=c.get("name","en-US-GuyNeural"); tries=max(1,int(c.get("retries",3))); error=None
 for i in range(tries):
  try:return asyncio.run(_synthesize(text,path,voice,c.get("rate","+0%"),c.get("pitch","+0Hz")))
  except Exception as e:
   error=e
   if i+1<tries:time.sleep(1.5*(i+1))
 if not shutil.which("espeak-ng") or not shutil.which("ffmpeg"):
  raise RuntimeError(f"Edge TTS failed after {tries} attempts for voice {voice}: {error}. Install espeak-ng for the offline fallback.")
 print(f"[VOICE] Edge TTS unavailable after retries ({error}); using free offline eSpeak NG fallback.")
 wav=path.with_suffix(".fallback.wav")
 try:
  proc=subprocess.run(["espeak-ng","-v","en-us","-s","165","-p","50","-w",str(wav),text],capture_output=True,text=True)
  if proc.returncode:raise RuntimeError(f"eSpeak NG failed: {proc.stderr[-1000:]}")
  with wave.open(str(wav),"rb") as f: total=f.getnframes()/float(f.getframerate())
  proc=subprocess.run(["ffmpeg","-y","-i",str(wav),"-codec:a","libmp3lame","-q:a","3",str(path)],capture_output=True,text=True)
  if proc.returncode:raise RuntimeError(f"FFmpeg MP3 conversion failed: {proc.stderr[-1000:]}")
  words=text.split(); weights=[max(1,len(word.strip(".,!?;:'\"()[]{}"))) + (1.5 if word[-1:] in ".!?;:" else 0) for word in words]
  scale=total/max(1,sum(weights)); cursor=0.0; result=[]
  for word,weight in zip(words,weights):
   start=cursor; cursor+=weight*scale; result.append({"text":word,"start":start,"end":cursor})
  return result
 finally:
  wav.unlink(missing_ok=True)
