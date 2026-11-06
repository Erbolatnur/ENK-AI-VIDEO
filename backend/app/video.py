"""FFmpeg-слой: демо-клипы, субтитры, склейка сцен. Только стандартная библиотека."""
import json, subprocess, tempfile, os

SIZES = {"9:16": (720, 1280), "16:9": (1280, 720), "1:1": (720, 720)}
FPS = 24


def _run(args):
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError("ffmpeg: " + r.stderr.strip()[-500:])


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height",
                        "-show_entries", "format=duration", "-of", "json", path],
                       capture_output=True, text=True, check=True)
    d = json.loads(r.stdout)
    v = next((s for s in d["streams"] if s["codec_type"] == "video"), {})
    return {"duration": float(d["format"]["duration"]), "width": v.get("width"), "height": v.get("height"),
            "streams": [s["codec_type"] for s in d["streams"]]}


def make_demo_clip(out, aspect, duration, seed=0, image=None):
    """DEMO-режим: настоящий MP4 без внешнего API (градиент или Ken-Burns по фото)."""
    w, h = SIZES[aspect]
    if image:
        src = ["-i", image]
        vf = (f"scale={w*2}:{h*2}:force_original_aspect_ratio=increase,crop={w*2}:{h*2},"
              f"zoompan=z='min(zoom+0.0015,1.3)':d={duration*FPS}:s={w}x{h}:fps={FPS},format=yuv420p")
    else:
        src = ["-f", "lavfi", "-i", f"gradients=s={w}x{h}:d={duration}:r={FPS}:speed=0.03:seed={seed}"
               ":c0=0x0b0b0b:c1=0x00ff88:c2=0x1a1a1a:c3=0x00cc66:nb_colors=4"]
        vf = "format=yuv420p"
    _run([*src, "-vf", vf, "-t", str(duration), "-r", str(FPS), "-c:v", "libx264",
          "-preset", "veryfast", "-movflags", "+faststart", "-an", out])


def make_srt(text, duration):
    """Автосубтитры: текст делится на фразы, время распределяется поровну."""
    parts = [p.strip() for p in text.replace("!", ".").replace("?", ".").split(".") if p.strip()] or [text]
    step = duration / len(parts)
    ts = lambda t: f"{int(t//3600):02}:{int(t%3600//60):02}:{int(t%60):02},{int(t%1*1000):03}"
    return "\n".join(f"{i+1}\n{ts(i*step)} --> {ts((i+1)*step)}\n{p}\n" for i, p in enumerate(parts))


def add_subtitles(video, srt_text, out):
    """Мягкие субтитры (mov_text) — не требуют libass; отдельная дорожка в MP4."""
    with tempfile.NamedTemporaryFile("w", suffix=".srt", delete=False, encoding="utf-8") as f:
        f.write(srt_text)
    try:
        _run(["-i", video, "-i", f.name, "-map", "0", "-map", "1", "-c:v", "copy", "-c:s", "mov_text",
              "-metadata:s:s:0", "language=rus", "-movflags", "+faststart", out])
    finally:
        os.unlink(f.name)


def concat(clips, out):
    """Редактор: объединение сцен одного формата."""
    ins = [x for c in clips for x in ("-i", c)]
    fc = "".join(f"[{i}:v]" for i in range(len(clips))) + f"concat=n={len(clips)}:v=1:a=0[v]"
    _run([*ins, "-filter_complex", fc, "-map", "[v]", "-c:v", "libx264", "-pix_fmt", "yuv420p",
          "-movflags", "+faststart", out])
