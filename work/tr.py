import json,sys,soundfile as sf
A=sf.read("a16.wav",dtype="float32")[0]
from faster_whisper import WhisperModel
try:
    m=WhisperModel("large-v3",device="cuda",compute_type="float16"); 
    list(m.transcribe(A,language="zh")[0])[:0]
except Exception as e:
    print("cuda fail",e); m=WhisperModel("large-v3",device="cpu",compute_type="int8")
segs,info=m.transcribe(A,language="zh",word_timestamps=True,beam_size=5,vad_filter=False,initial_prompt="以下是一首普通话歌曲《山脚》的歌词。",condition_on_previous_text=False)
out=[]
for s in segs:
    out.append(dict(s=s.start,e=s.end,t=s.text,w=[(w.start,w.end,w.word) for w in (s.words or [])]))
    print(f"{s.start:7.2f} {s.end:7.2f} {s.text}",flush=True)
json.dump(out,open("tr.json","w",encoding="utf8"),ensure_ascii=False)
