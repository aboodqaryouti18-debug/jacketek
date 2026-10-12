#!/usr/bin/env bash
# Assemble the JACKETEK 25 s reel from the seven shots + voice-over.
# Runs where ffmpeg is available (the Higgsfield sandbox). Inputs in the cwd:
#   c1.mp4 .. c7.mp4  (shot order below), vo.wav
# Output: jacketek_reel_25s.mp4 (1080x1920, 24 fps, H.264 + AAC)
#
#  #  shot                      used  timeline (after 0.4 s crossfades)
#  1  front on ice blue         5.0   0.0 - 5.0   Scene 1 the idea
#  2  chest lettering           3.0   4.6 - 7.6   Scene 2 personalisation
#  3  sleeve patch (prep.sh)    3.0   7.2 - 10.2
#  4  JK patch macro            3.2   9.8 - 13.0  Scene 3 embroidery
#  5  needle stitching macro    5.0   12.6 - 17.6
#  6  back SENIOR 2027          4.2   17.2 - 21.4 Scene 4 finished jacket
#  7  hero (prep.sh)            4.0   21.0 - 25.0
set -euo pipefail
D=(5.0 3.0 3.0 3.2 5.0 4.2 4.0)
X=0.4
VO_START=${VO_START:-0.6}
VO_TEMPO=${VO_TEMPO:-1.0}

in=() ; pre="" ; i=0
for d in "${D[@]}"; do
  n=$((i+1))
  in+=(-i "c$n.mp4")
  pre+="[$i:v]trim=0:$d,setpts=PTS-STARTPTS,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=24,format=yuv420p,setsar=1[v$i];"
  i=$((i+1))
done

DLIST=$(IFS=,; echo "${D[*]}")
chain="" ; last="v0" ; acc=0
for k in 1 2 3 4 5 6; do
  acc=$(python3 -c "print(round(sum([$DLIST][:$k]) - $k*$X, 3))")
  chain+="[$last][v$k]xfade=transition=fade:duration=$X:offset=$acc[x$k];"
  last="x$k"
done

# machine sound of shot 5 starts at 12.6 s, kept low under the narration
SFX_START=12.6
filter="$pre$chain[$last]fade=t=in:st=0:d=0.3[vout];"
filter+="[4:a]atrim=0:5.0,asetpts=PTS-STARTPTS,afade=t=in:d=0.4,afade=t=out:st=4.4:d=0.6,volume=0.22,adelay=$(python3 -c "print(int($SFX_START*1000))")|$(python3 -c "print(int($SFX_START*1000))")[sfx];"
filter+="[7:a]atempo=$VO_TEMPO,adelay=$(python3 -c "print(int($VO_START*1000))")|$(python3 -c "print(int($VO_START*1000))"),volume=1.0[vo];"
filter+="[vo][sfx]amix=inputs=2:duration=longest:normalize=0,apad,atrim=0:25,afade=t=out:st=24.4:d=0.6,loudnorm=I=-14:TP=-1.5:LRA=11[aout]"

ffmpeg -y -hide_banner -loglevel error "${in[@]}" -i vo.wav \
  -filter_complex "$filter" -map "[vout]" -map "[aout]" \
  -t 25 -c:v libx264 -preset slow -crf 16 -profile:v high -pix_fmt yuv420p -r 24 \
  -c:a aac -b:a 192k -ar 48000 -movflags +faststart jacketek_reel_25s.mp4
ffprobe -v error -show_entries stream=codec_type,width,height,r_frame_rate:format=duration -of compact jacketek_reel_25s.mp4
