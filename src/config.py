from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str
    host: str
    sensenova_api_key: str = ""
    seedance_api_key: str = ""
    seedance_base_url: str = "https://api.scnet.cn/api/llm/v1"
    image_model: str = "agnes-image-2.1-flash"
    video_model: str = "agnes-video-v2.0"
    poll_interval_sec: float = 5.0
    poll_timeout_sec: float = 360.0
    output_dir: Path = Path("output")

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> Settings:
        if env_file is None:
            env_file = Path.cwd() / ".env"
        if env_file.exists():
            load_dotenv(env_file)

        api_key = os.getenv("AGNES_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError(
                "AGNES_API_KEY 未配置。请在 .env 中设置,或参考 .env.example。"
            )
        base_url = os.getenv("AGNES_BASE_URL", "https://apihub.agnes-ai.com/v1").rstrip("/")
        parsed = urlparse(base_url)
        host = f"{parsed.scheme}://{parsed.netloc}"
        sensenova_api_key = os.getenv("SENSENOVA_API_KEY", "").strip()
        seedance_api_key = os.getenv("SEEDANCE_API_KEY", "").strip()
        seedance_base_url = os.getenv(
            "SEEDANCE_BASE_URL", "https://api.scnet.cn/api/llm/v1"
        ).rstrip("/")
        return cls(
            api_key=api_key,
            base_url=base_url,
            host=host,
            sensenova_api_key=sensenova_api_key,
            seedance_api_key=seedance_api_key,
            seedance_base_url=seedance_base_url,
        )
