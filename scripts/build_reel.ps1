# Dựng reel dọc 9:16 từ clip thô (đã dùng cho MEO_COOKIE). Chạy từ thư mục gốc repo.
# Bước 1 (thủ công): chuẩn hoá clip -> work/c1..cN.mp4 (1080x1920, 30fps, nền mờ, bỏ audio)
# Bước 2: python -I scripts/motion.py (trong work/) -> motion.json, chọn đoạn -> work/plan.json
# Bước 3: npx remotion render EditOverlay ../work/overlay.mov --codec=prores --prores-profile=4444 --pixel-format=yuva444p10le --image-format=png (trong remotion-project)
# Bước 4: chạy script này để ghép.
param([string]$Music="Raw\Unheard - Void (freetouse.com).mp3",[string]$Out="Output video\reel.mp4",[double]$Len=3.5,[int]$Dur=14)
$plan=Get-Content work\plan.json | ConvertFrom-Json
$in=@(); $f=""; $i=0
foreach($p in $plan){ $in+=@('-i',"work\c$($p.clip).mp4"); $f+="[$i`:v]trim=start=$($p.start):duration=$Len,setpts=PTS-STARTPTS[v$i];"; $i++ }
$n=$plan.Count; $labels=(0..($n-1)|%{"[v$_]"}) -join ""
$f+="${labels}concat=n=${n}:v=1:a=0[base];[base][$n`:v]overlay=format=auto,format=yuv420p[v];[$($n+1)`:a]atrim=0:$Dur,afade=t=in:d=0.5,afade=t=out:st=$($Dur-1.5):d=1.5,loudnorm=I=-14:TP=-1.5:LRA=11[a]"
ffmpeg -y @in -i work\overlay.mov -i $Music -filter_complex $f -map "[v]" -map "[a]" -t $Dur -r 30 -c:v libx264 -crf 18 -c:a aac -b:a 192k -movflags +faststart $Out
