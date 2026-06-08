from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ImageRequest(BaseModel):
    model: str = "agnes-image-2.1-flash"
    prompt: str
    size: str = "1024x768"
    image: list[str] | None = None
    return_base64: bool = False
    extra_body: dict | None = None


class ImageResponse(BaseModel):
    created: int
    data: list[dict] = Field(default_factory=list)


class VideoCreateRequest(BaseModel):
    model: str = "agnes-video-v2.0"
    prompt: str
    image: str | list[str] | None = None
    mode: Literal["ti2vid", "keyframes"] | None = None
    height: int = 768
    width: int = 1152
    num_frames: int = 121
    frame_rate: int = 24
    num_inference_steps: int | None = None
    seed: int | None = None
    negative_prompt: str | None = None
    extra_body: dict | None = None

    @field_validator("num_frames")
    @classmethod
    def validate_num_frames(cls, v: int) -> int:
        if v > 441:
            raise ValueError(f"num_frames 不能超过 441, 得到 {v}")
        if (v - 1) % 8 != 0:
            raise ValueError(f"num_frames 必须满足 8n+1 规则, 得到 {v}")
        return v

    @field_validator("frame_rate")
    @classmethod
    def validate_frame_rate(cls, v: int) -> int:
        if v < 1 or v > 60:
            raise ValueError(f"frame_rate 范围 1-60, 得到 {v}")
        return v


class VideoCreateResponse(BaseModel):
    id: str | None = None
    task_id: str | None = None
    video_id: str | None = None
    object: str | None = None
    model: str | None = None
    status: str | None = None
    progress: int | None = None
    created_at: int | None = None
    seconds: str | None = None
    size: str | None = None


class VideoQueryResponse(BaseModel):
    id: str | None = None
    video_id: str | None = None
    model: str | None = None
    status: str | None = None
    progress: int | None = None
    seconds: str | None = None
    size: str | None = None
    video_url: str | None = None
    url: str | None = None
    output_url: str | None = None
    result_url: str | None = None
    remixed_from_video_id: str | None = None
    error: dict | None = None
