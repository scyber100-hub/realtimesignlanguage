RTMP/LL-HLS 파이프라인 예시(지연 최적화)

입력 분리(오디오 추출 → ASR 송신)
```bash
# RTMP 입력에서 오디오만 추출해 16k PCM으로 파이프(리눅스 예)
ffmpeg -fflags nobuffer -i rtmp://origin/live/stream \
  -vn -ac 1 -ar 16000 -c:a pcm_s16le -f s16le - \
  | your-asr-client --rate 16000 --bytes 2
```

Unity 인셋 + 원본 합성 → RTMP 송출
```bash
# Unity 인셋(알파) + 원본 영상 PiP 컴포지트(우하단 25%)
ffmpeg -fflags nobuffer -threads 2 \
  -i rtmp://origin/live/stream \
  -i rtmp://unity/alpha \
  -filter_complex "[1:v]scale=iw*0.25:ih*0.25 [pip]; [0:v][pip] overlay=W-w-40:H-h-40:format=auto" \
  -c:v libx264 -preset veryfast -tune zerolatency -g 30 -keyint_min 30 -sc_threshold 0 \
  -c:a aac -b:a 128k -f flv rtmp://output/live/with_sign
```

LL-HLS 패키징(선택)
```bash
ffmpeg -fflags nobuffer -i rtmp://output/live/with_sign \
  -c:v copy -c:a copy \
  -hls_time 1 -hls_list_size 6 -hls_flags delete_segments+append_list \
  -f hls /var/www/hls/stream.m3u8
```

지연 낮추기 팁
- `-fflags nobuffer` / `-probesize` `-analyzeduration` 축소
- 인코더 `-preset veryfast` + `-tune zerolatency` + 짧은 `-g`
- 파이프/소켓 버퍼 최소화, 네트워크 RTT 최적화

