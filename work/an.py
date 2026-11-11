import librosa,numpy as np,json
y,sr=librosa.load("a44.wav",sr=22050,mono=True)
tempo,beats=librosa.beat.beat_track(y=y,sr=sr,units='time')
print("tempo",tempo,"nbeats",len(beats),"first",beats[:8])
hop=512
rms=librosa.feature.rms(y=y,frame_length=2048,hop_length=hop)[0]
t=librosa.frames_to_time(np.arange(len(rms)),sr=sr,hop_length=hop)
# 2s energy profile
for a in range(0,int(t[-1])+1,4):
    m=(t>=a)&(t<a+4); v=rms[m].mean()
    print(f"{a:4d} {v:.4f} "+"#"*int(v*200))
S=np.abs(librosa.stft(y,n_fft=2048,hop_length=hop))
f=librosa.fft_frequencies(sr=sr,n_fft=2048)
bands=dict(low=(20,150),mid=(150,2000),high=(2000,10000))
env={k:S[(f>=lo)&(f<hi)].mean(0) for k,(lo,hi) in bands.items()}
on=librosa.onset.onset_strength(y=y,sr=sr,hop_length=hop)
np.savez("feat.npz",t=t,rms=rms,on=on,beats=beats,**env)
