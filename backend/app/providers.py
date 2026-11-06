"""Единый интерфейс ИИ-провайдеров. Новый движок = новый класс + строка в REGISTRY."""
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Optional
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
    """Заготовка под платные API. Эндпоинты НЕ выдуманы: их нужно взять из официальной
    документации выбранной модели и указать в переменных окружения."""
    key_env = ""
    model_env = ""

    def available(self): return bool(os.getenv(self.key_env) and os.getenv(self.model_env))

    def generate(self, req, out_path, progress):
        if not self.available():
            raise RuntimeError(f"{self.title}: задайте {self.key_env} и {self.model_env}")
        raise NotImplementedError(f"{self.title}: вызов API не реализован — "
                                  "добавьте по официальной документации модели")


class FalProvider(_ApiProvider):
    id, title, key_env, model_env = "fal", "fal.ai", "FAL_KEY", "FAL_MODEL_ID"


class ReplicateProvider(_ApiProvider):
    id, title, key_env, model_env = "replicate", "Replicate", "REPLICATE_API_TOKEN", "REPLICATE_MODEL"


REGISTRY = {p.id: p() for p in (DemoProvider, FalProvider, ReplicateProvider)}
