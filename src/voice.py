from __future__ import annotations
import asyncio,time
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
 raise RuntimeError(f"Edge TTS failed after {tries} attempts for voice {voice}: {error}")
