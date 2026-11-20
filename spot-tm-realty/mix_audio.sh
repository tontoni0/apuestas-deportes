#!/usr/bin/env bash
# Mixes music, clip ambience and SFX for the 17.6 s spot.
set -euo pipefail
cd "$(dirname "$0")"
D=17.6
ffmpeg -v error -y \
  -i audio/music.mp3 \
  -i public/clipA.mp4 \
  -i public/clipB.mp4 \
  -i audio/notify.mp3 \
  -i audio/impact.mp3 \
  -i audio/whoosh.mp3 \
  -i audio/notify_soft.mp3 \
  -i audio/whoosh.mp3 \
  -i audio/notify_soft.mp3 \
  -i audio/mission_complete.mp3 \
  -i audio/whoosh.mp3 \
  -i audio/impact_soft.mp3 \
  -filter_complex "
    [0:a]atrim=0:${D},volume=-5dB,afade=t=out:st=16.6:d=1.0[mus];
    [1:a]atrim=0:8.1,volume=9dB,afade=t=in:d=0.3,afade=t=out:st=7.7:d=0.4[ambA];
    [2:a]atrim=0:5.02,volume=-7dB,afade=t=out:st=4.6:d=0.4,adelay=8100|8100[ambB];
    [3:a]volume=-4dB,adelay=400|400[s1];
    [4:a]volume=-1dB,adelay=3070|3070[s2];
    [5:a]volume=-4dB,adelay=5500|5500[s3];
    [6:a]volume=-5dB,adelay=5800|5800[s4];
    [7:a]volume=-1dB,adelay=7960|7960[s5];
    [8:a]volume=-5dB,adelay=8250|8250[s6];
    [9:a]volume=0dB,adelay=10540|10540[s7];
    [10:a]volume=-5dB,adelay=13000|13000[s8];
    [11:a]volume=-7dB,adelay=15000|15000[s9];
    [mus][ambA][ambB][s1][s2][s3][s4][s5][s6][s7][s8][s9]amix=inputs=12:duration=first:normalize=0,
    loudnorm=I=-14:TP=-1.0:LRA=11,aresample=48000[out]" \
  -map "[out]" -t ${D} -c:a pcm_s16le out/mix.wav
echo "mix ok"
