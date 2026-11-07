"""Единый интерфейс ИИ-провайдеров. Новый движок = новый класс + строка в REGISTRY."""
import json, os, shutil, time, urllib.error, urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Optional
from urllib.parse import urlparse
from . import video


@dataclass
class GenRequest:
    prompt: str
    aspect: str
    duration: int
    image_path: Optional[str] = None


class Provider(ABC):
    id: str
    title: str
    modes = ("text", "image")

    @abstractmethod
    def available(self) -> bool: ...

    @abstractmethod
    def generate(self, req: GenRequest, out_path: str, progress: Callable[[int], None]) -> None: ...


class DemoProvider(Provider):
    id, title = "demo", "DEMO (без API-ключа)"

    def available(self): return True

    def generate(self, req, out_path, progress):
        progress(10)
        video.make_demo_clip(out_path, req.aspect, req.duration, seed=hash(req.prompt) % 1000, image=req.image_path)
        progress(100)


class _ApiProvider(Provider):
    key_env = ""
    model_env = ""

    def available(self): return bool(os.getenv(self.key_env) and os.getenv(self.model_env))


def _http(method, url, key, body=None, timeout=60):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method,
                               headers={"Authorization": f"Key {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"fal.ai {e.code}: {e.read().decode(errors='replace')[:300]}")


def _trusted(url):
    """Ключ уходит только на домены очереди fal.ai (ответ API содержит готовые status_url/response_url)."""
    h = urlparse(url)
    return h.scheme == "https" and (h.hostname or "").endswith(("fal.run", "falrun.com"))


class FalProvider(_ApiProvider):
    """fal.ai Queue API (docs: fal.ai/docs): POST queue.fal.run/{model_id} -> status_url -> response_url -> video.url.
    Поля входа prompt/aspect_ratio/duration и выход video.url общие у text-to-video моделей каталога fal.ai,
    но у каждой модели своя схема: сверяйте её на странице выбранной модели."""
    id, title, key_env, model_env = "fal", "fal.ai", "FAL_KEY", "FAL_MODEL_ID"
    TIMEOUT = 600

    def generate(self, req, out_path, progress):
        if not self.available():
            raise RuntimeError("fal.ai: задайте FAL_KEY и FAL_MODEL_ID")
        if req.image_path:
            raise RuntimeError("fal.ai: Image-to-Video для этой модели не подключён. Уберите фото или выберите DEMO")
        limit = int(os.getenv("FAL_MAX_DURATION", "10"))
        if req.duration > limit:
            raise RuntimeError(f"Платная модель: максимум {limit} с (FAL_MAX_DURATION)")
        key, model = os.environ["FAL_KEY"], os.environ["FAL_MODEL_ID"]
        sub = _http("POST", f"https://queue.fal.run/{model}", key,
                    {"prompt": req.prompt, "aspect_ratio": req.aspect, "duration": req.duration})
        if not (_trusted(sub.get("status_url", "")) and _trusted(sub.get("response_url", ""))):
            raise RuntimeError("fal.ai: неожиданный ответ очереди")
        progress(10)
        deadline = time.time() + self.TIMEOUT
        while True:
            st = _http("GET", sub["status_url"], key)
            if st.get("status") == "COMPLETED":
                break
            progress(20 if st.get("status") == "IN_QUEUE" else 50)
            if time.time() > deadline:
                raise RuntimeError("fal.ai: время ожидания вышло")
            time.sleep(3)
        url = (_http("GET", sub["response_url"], key).get("video") or {}).get("url", "")
        if not url.startswith("https://"):
            raise RuntimeError("fal.ai: в ответе нет ссылки на видео")
        progress(85)
        with urllib.request.urlopen(url, timeout=120) as r, open(out_path, "wb") as f:
            shutil.copyfileobj(r, f)
        progress(100)


class ReplicateProvider(_ApiProvider):
    id, title, key_env, model_env = "replicate", "Replicate", "REPLICATE_API_TOKEN", "REPLICATE_MODEL"

    def generate(self, req, out_path, progress):
        raise NotImplementedError("Replicate: вызов API не реализован — добавьте по официальной документации модели")


REGISTRY = {p.id: p() for p in (DemoProvider, FalProvider, ReplicateProvider)}
