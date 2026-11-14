import subprocess, numpy as np, sys, json, shutil
ff = shutil.which("ffmpeg") or "ffmpeg"
out = {}
for i in range(1,5):
    W,H,FPS=54,96,10
    p = subprocess.run([ff,"-v","error","-i",f"c{i}.mp4","-vf",f"fps={FPS},scale={W}:{H},format=gray","-f","rawvideo","-"],capture_output=True)
    a = np.frombuffer(p.stdout,np.uint8).reshape(-1,H,W).astype(np.float32)
    d = np.abs(np.diff(a,axis=0)).mean(axis=(1,2))
    # smooth over 1s
    k = np.ones(FPS)/FPS
    s = np.convolve(d,k,mode="same")
    out[i] = {"fps":FPS,"motion":[round(float(x),2) for x in s],"dur":len(a)/FPS}
    print(i, "dur",len(a)/FPS,"mean",round(float(s.mean()),2),"p25",round(float(np.percentile(s,25)),2),"p75",round(float(np.percentile(s,75)),2),"max",round(float(s.max()),2))
json.dump(out,open("motion.json","w"))
