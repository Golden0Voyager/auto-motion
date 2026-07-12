from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class SeedanceMedia(BaseModel):
    type: Literal["first_frame", "last_frame", "reference_image", "reference_video", "reference_audio"]
    url: str


class SeedanceInput(BaseModel):
    prompt: str
    images: list[str] | None = None
    media: list[SeedanceMedia] | None = None


class SeedanceParameters(BaseModel):
    generate_audio: bool = False
    ratio: str = "16:9"
    duration: int = 5
    resolution: str = "720p"
    watermark: bool = False
    seed: int | None = None
    camera_fixed: bool = False

    @field_validator("duration")
    @classmethod
    def validate_duration(cls, v: int) -> int:
        if v < 4 or v > 15:
            raise ValueError(f"duration 范围 4-15 秒, 得到 {v}")
        return v

    @field_validator("resolution")
    @classmethod
    def validate_resolution(cls, v: str) -> str:
        valid = {"480p", "720p", "1080p"}
        if v not in valid:
            raise ValueError(f"resolution 必须是 {valid} 之一, 得到 {v}")
        return v

    @field_validator("ratio")
    @classmethod
    def validate_ratio(cls, v: str) -> str:
        valid = {"adaptive", "16:9", "9:16"}
        if v not in valid:
            raise ValueError(f"ratio 必须是 {valid} 之一, 得到 {v}")
        return v


class SeedanceRequest(BaseModel):
    model: str = "Seedance2.0"
    input: SeedanceInput
    parameters: SeedanceParameters = Field(default_factory=SeedanceParameters)


class SeedanceOutput(BaseModel):
    task_id: str | None = None
    task_status: str | None = None
    submit_time: str | None = None
    end_time: str | None = None
    results: list[str] | None = None
    error_code: str | None = None
    error_message: str | None = None


class SeedanceTokenUsage(BaseModel):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class SeedanceUsage(BaseModel):
    video_count: int | None = None
    video_duration: int | None = None
    resolution: str | None = None
    ratio: str | None = None
    token_usage: SeedanceTokenUsage | None = None


class HappyHorseInput(BaseModel):
    prompt: str


class HappyHorseParameters(BaseModel):
    resolution: str = "720p"
    ratio: str = "16:9"
    duration: int = 5
    watermark: bool = True
    seed: int | None = None

    @field_validator("duration")
    @classmethod
    def validate_duration(cls, v: int) -> int:
        if v < 3 or v > 15:
            raise ValueError(f"duration 范围 3-15 秒, 得到 {v}")
        return v

    @field_validator("resolution")
    @classmethod
    def validate_resolution(cls, v: str) -> str:
        valid = {"720p", "1080p"}
        if v not in valid:
            raise ValueError(f"resolution 必须是 {valid} 之一, 得到 {v}")
        return v

    @field_validator("ratio")
    @classmethod
    def validate_ratio(cls, v: str) -> str:
        valid = {"16:9", "9:16", "1:1", "4:3", "3:4", "4:5", "5:4", "9:21", "21:9"}
        if v not in valid:
            raise ValueError(f"ratio 必须是 {valid} 之一, 得到 {v}")
        return v


class HappyHorseRequest(BaseModel):
    model: str = "HappyHorse-1.0-T2V"
    input: HappyHorseInput
    parameters: HappyHorseParameters = Field(default_factory=HappyHorseParameters)


class WanInput(BaseModel):
    prompt: str
    negative_prompt: str | None = None
    audio_url: str | None = None


class WanParameters(BaseModel):
    resolution: str = "720p"
    ratio: str = "16:9"
    duration: int = 5
    prompt_extend: bool | None = None
    watermark: bool = False
    seed: int | None = None

    @field_validator("duration")
    @classmethod
    def validate_duration(cls, v: int) -> int:
        if v < 2 or v > 15:
            raise ValueError(f"duration 范围 2-15 秒, 得到 {v}")
        return v

    @field_validator("resolution")
    @classmethod
    def validate_resolution(cls, v: str) -> str:
        valid = {"480p", "720p", "1080p"}
        if v not in valid:
            raise ValueError(f"resolution 必须是 {valid} 之一, 得到 {v}")
        return v

    @field_validator("ratio")
    @classmethod
    def validate_ratio(cls, v: str) -> str:
        valid = {"16:9", "9:16"}
        if v not in valid:
            raise ValueError(f"ratio 必须是 {valid} 之一, 得到 {v}")
        return v


class WanRequest(BaseModel):
    model: str = "Wan2.7-T2V"
    input: WanInput
    parameters: WanParameters = Field(default_factory=WanParameters)


class SeedanceCreateResponse(BaseModel):
    request_id: str | None = None
    output: SeedanceOutput | None = None


class SeedanceTaskResponse(BaseModel):
    request_id: str | None = None
    output: SeedanceOutput | None = None
    usage: SeedanceUsage | None = None


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


class QwenImageInput(BaseModel):
    prompt: str
    negative_prompt: str | None = None


class QwenImageParameters(BaseModel):
    size: str = "2048*2048"
    n: int = 1
    negative_prompt: str | None = None
    prompt_extend: bool = True
    watermark: bool = False
    seed: int | None = None

    @field_validator("n")
    @classmethod
    def clamp_n(cls, v: int) -> int:
        return max(1, min(6, v))

    @field_validator("size")
    @classmethod
    def validate_size(cls, v: str) -> str:
        if "*" not in v:
            raise ValueError(f"size 格式应为 宽*高, 得到 {v}")
        try:
            w, h = (int(x) for x in v.split("*"))
        except ValueError:
            raise ValueError(f"size 解析失败, 应为 宽*高 的整数, 得到 {v}") from None
        pixels = w * h
        if pixels < 512 * 512 or pixels > 2048 * 2048:
            raise ValueError(f"总像素需在 512*512 至 2048*2048 之间, 得到 {w}x{h}={pixels}")
        return v


class QwenImageRequest(BaseModel):
    model: str = "Qwen-Image-2.0"
    input: QwenImageInput
    parameters: QwenImageParameters = Field(default_factory=QwenImageParameters)


class QwenImageOutput(BaseModel):
    task_id: str | None = None
    task_status: str | None = None
    results: list[str] | None = None


class QwenImageUsage(BaseModel):
    image_count: int | None = None
    resolution: str | None = None


class QwenImageResponse(BaseModel):
    request_id: str | None = None
    output: QwenImageOutput | None = None
    usage: QwenImageUsage | None = None


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
