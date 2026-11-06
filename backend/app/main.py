"""ENK AI VIDEO — API. Хранилище задач в памяти (MVP); Postgres/Redis/S3 — см. README."""
import os, time, uuid, threading, collections
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, Header, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from . import providers, video

DATA = Path(os.getenv("ENK_DATA_DIR", "./data")); DATA.mkdir(parents=True, exist_ok=True)
TOKENS = dict(p.split(":", 1)[::-1] for p in os.getenv("ENK_TOKENS", "demo:demo-token").split(",") if ":" in p)
LIMIT, WINDOW = int(os.getenv("ENK_RATE_LIMIT", "20")), 60
JOBS: dict = {}; HITS = collections.defaultdict(collections.deque); LOCK = threading.Lock()
app = FastAPI(title="ENK AI VIDEO")


bearer = HTTPBearer(auto_error=False)


def user(cred: Optional[HTTPAuthorizationCredentials] = Depends(bearer)) -> str:
    u = TOKENS.get(cred.credentials if cred else "")
    if not u: raise HTTPException(401, "Неверный токен")
    with LOCK:
        q, now = HITS[u], time.time()
        while q and now - q[0] > WINDOW: q.popleft()
        if len(q) >= LIMIT: raise HTTPException(429, "Слишком много запросов")
        q.append(now)
    return u


def own(job_id: str, u: str) -> dict:
    j = JOBS.get(job_id)
    if not j or j["user"] != u: raise HTTPException(404, "Проект не найден")  # чужие видео не раскрываем
    return j


def run(job_id: str, req: providers.GenRequest, model: str, subs: bool):
    j = JOBS[job_id]; out = DATA / f"{job_id}.mp4"; j["status"] = "processing"
    try:
        providers.REGISTRY[model].generate(req, str(out), lambda p: j.update(progress=p))
        if subs:
            tmp = DATA / f"{job_id}.raw.mp4"; out.rename(tmp)
            video.add_subtitles(str(tmp), video.make_srt(req.prompt, req.duration), str(out)); tmp.unlink()
        j.update(status="done", progress=100)
    except Exception as e:
        j.update(status="failed", error=str(e)[:300])


@app.get("/api/models")
def models(_: str = Depends(user)):
    return [{"id": p.id, "title": p.title, "available": p.available()} for p in providers.REGISTRY.values()]


@app.post("/api/jobs", status_code=202)
async def create(bg: BackgroundTasks, u: str = Depends(user), prompt: str = Form(..., min_length=1, max_length=1000),
                 aspect: str = Form("9:16"), duration: int = Form(5, ge=2, le=15), model: str = Form("demo"),
                 subtitles: bool = Form(False), image: Optional[UploadFile] = File(None)):
    if aspect not in video.SIZES: raise HTTPException(422, "Формат: 9:16, 16:9 или 1:1")
    prov = providers.REGISTRY.get(model)
    if not prov or not prov.available(): raise HTTPException(422, "Модель недоступна")
    jid, img = uuid.uuid4().hex, None
    if image:
        data = await image.read()
        if image.content_type not in ("image/png", "image/jpeg") or len(data) > 10_000_000:
            raise HTTPException(422, "Нужен PNG/JPEG до 10 МБ")
        img = str(DATA / f"{jid}.src"); Path(img).write_bytes(data)
    JOBS[jid] = {"id": jid, "user": u, "prompt": prompt, "aspect": aspect, "duration": duration, "model": model,
                 "status": "queued", "progress": 0, "created": time.time()}
    bg.add_task(run, jid, providers.GenRequest(prompt, aspect, duration, img), model, subtitles)
    return {"id": jid}


@app.get("/api/jobs")
def history(u: str = Depends(user)):
    return sorted((j for j in JOBS.values() if j["user"] == u), key=lambda j: -j["created"])


@app.get("/api/jobs/{job_id}")
def get(job_id: str, u: str = Depends(user)): return own(job_id, u)


@app.get("/api/jobs/{job_id}/download")
def download(job_id: str, u: str = Depends(user)):
    if own(job_id, u)["status"] != "done": raise HTTPException(409, "Видео ещё не готово")
    return FileResponse(DATA / f"{job_id}.mp4", media_type="video/mp4", filename=f"enk-{job_id[:8]}.mp4")
