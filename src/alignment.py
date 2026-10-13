from __future__ import annotations
import difflib,re

def _tokens(text): return [t.lower().replace("’","'") for t in re.findall(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)*",text)]

def align_paragraphs(paragraphs,words,audio_duration):
    """Fuzzy-align script paragraphs to ASR words; low-confidence matches fall back proportionally."""
    if not paragraphs:return []
    if not words: raise ValueError("Cannot align paragraphs: transcription contains no words.")
    script=[_tokens(p) for p in paragraphs]; flat=[t for para in script for t in para]
    audio=[(_tokens(str(w.get("text","")))+[""])[0] for w in words]
    duration=max(float(audio_duration),float(words[-1]["end"]),.01)
    if not flat: raise ValueError("Cannot align an empty script.")
    matcher=difflib.SequenceMatcher(a=flat,b=audio,autojunk=False)
    matches=sum(n for _,_,n in matcher.get_matching_blocks())
    ratio=matches/max(1,len(flat))
    if ratio < .45 or abs(len(flat)-len(audio))/max(len(flat),len(audio),1) > .65:
        print(f"[ALIGNMENT WARNING] Script/transcription match is weak ({ratio:.0%}); using proportional word-count timing.")
        results=[]; total=sum(max(1,len(p)) for p in script); cursor=0
        for para in script:
            count=max(1,len(para)); start=cursor/total*duration; cursor+=count
            results.append({"start":start,"end":cursor/total*duration})
        results[-1]["end"]=duration
        return results
    mapping={}
    for a,b,n in matcher.get_matching_blocks():
        for k in range(n):mapping[a+k]=b+k
    total=max(1,len(flat)); results=[]; cursor=0; previous=0.
    for para in script:
        n=len(para); idx=[mapping[i] for i in range(cursor,cursor+n) if i in mapping]
        if len(idx)<max(1,int(n*.35)):
            start=cursor/total*duration; end=(cursor+n)/total*duration
            print(f"[ALIGNMENT WARNING] Paragraph {len(results)+1} had weak word matches; using proportional timing.")
        else:
            start=float(words[min(idx)]["start"]); end=float(words[max(idx)]["end"])
        start=max(previous,min(start,duration-.01)); end=max(start+.03,min(end,duration))
        results.append({"start":start,"end":end}); previous=end; cursor+=n
    results[0]["start"]=0.
    for i in range(1,len(results)):
        boundary=(results[i-1]["end"]+results[i]["start"])/2
        results[i-1]["end"]=boundary; results[i]["start"]=boundary
    results[-1]["end"]=duration
    return results
