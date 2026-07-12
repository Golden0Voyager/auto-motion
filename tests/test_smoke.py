from __future__ import annotations


def test_models_basic() -> None:
    from src.models import ImageRequest, VideoCreateRequest

    img = ImageRequest(prompt="a cat", size="1024x768")
    assert img.model == "agnes-image-2.1-flash"
    assert img.size == "1024x768"

    vid = VideoCreateRequest(prompt="a cat walking", num_frames=121, frame_rate=24)
    assert vid.model == "agnes-video-v2.0"
    assert vid.num_frames == 121


def test_video_frames_rule() -> None:
    from src.models import VideoCreateRequest

    for n in (81, 121, 161, 241, 441):
        VideoCreateRequest(prompt="x", num_frames=n)
        assert (n - 1) % 8 == 0, f"num_frames={n} 违反 8n+1 规则"


def test_video_frames_validation_rejects_invalid() -> None:
    from pydantic import ValidationError

    from src.models import VideoCreateRequest

    try:
        VideoCreateRequest(prompt="x", num_frames=100)
        assert False, "应拒绝 num_frames=100"
    except ValidationError:
        pass

    try:
        VideoCreateRequest(prompt="x", num_frames=500)
        assert False, "应拒绝 num_frames=500 (>441)"
    except ValidationError:
        pass


def test_video_frame_rate_validation() -> None:
    from pydantic import ValidationError

    from src.models import VideoCreateRequest

    try:
        VideoCreateRequest(prompt="x", frame_rate=0)
        assert False, "应拒绝 frame_rate=0"
    except ValidationError:
        pass

    try:
        VideoCreateRequest(prompt="x", frame_rate=61)
        assert False, "应拒绝 frame_rate=61"
    except ValidationError:
        pass

    v = VideoCreateRequest(prompt="x", frame_rate=30)
    assert v.frame_rate == 30


# ── HappyHorse model ──────────────────────────────────────────────────


def test_happyhorse_basic() -> None:
    from src.models import HappyHorseRequest

    req = HappyHorseRequest(input={"prompt": "a cat"})
    assert req.model == "HappyHorse-1.0-T2V"
    assert req.input.prompt == "a cat"
    assert req.parameters.resolution == "720p"
    assert req.parameters.ratio == "16:9"
    assert req.parameters.duration == 5
    assert req.parameters.watermark is True


def test_happyhorse_accepts_valid_duration() -> None:
    from src.models import HappyHorseParameters

    for d in (3, 5, 10, 15):
        p = HappyHorseParameters(duration=d)
        assert p.duration == d

    p2 = HappyHorseParameters()
    assert p2.duration == 5


def test_happyhorse_rejects_duration_below_3() -> None:
    from pydantic import ValidationError

    from src.models import HappyHorseParameters

    try:
        HappyHorseParameters(duration=2)
        assert False, "应拒绝 duration=2 (<3)"
    except ValidationError:
        pass

    try:
        HappyHorseParameters(duration=0)
        assert False, "应拒绝 duration=0"
    except ValidationError:
        pass


def test_happyhorse_rejects_duration_above_15() -> None:
    from pydantic import ValidationError

    from src.models import HappyHorseParameters

    try:
        HappyHorseParameters(duration=16)
        assert False, "应拒绝 duration=16 (>15)"
    except ValidationError:
        pass


def test_happyhorse_accepts_valid_ratios() -> None:
    from src.models import HappyHorseParameters

    valid_ratios = ("16:9", "9:16", "1:1", "4:3", "3:4", "4:5", "5:4", "9:21", "21:9")
    for r in valid_ratios:
        p = HappyHorseParameters(ratio=r)
        assert p.ratio == r


def test_happyhorse_rejects_invalid_ratio_adaptive() -> None:
    from pydantic import ValidationError

    from src.models import HappyHorseParameters

    try:
        HappyHorseParameters(ratio="adaptive")
        assert False, "应拒绝 ratio=adaptive (HappyHorse 不支持)"
    except ValidationError:
        pass


def test_happyhorse_rejects_invalid_ratio() -> None:
    from pydantic import ValidationError

    from src.models import HappyHorseParameters

    try:
        HappyHorseParameters(ratio="16:10")
        assert False, "应拒绝 ratio=16:10"
    except ValidationError:
        pass


def test_happyhorse_accepts_valid_resolutions() -> None:
    from src.models import HappyHorseParameters

    for r in ("720p", "1080p"):
        p = HappyHorseParameters(resolution=r)
        assert p.resolution == r


def test_happyhorse_rejects_480p() -> None:
    from pydantic import ValidationError

    from src.models import HappyHorseParameters

    try:
        HappyHorseParameters(resolution="480p")
        assert False, "应拒绝 resolution=480p (HappyHorse 不支持)"
    except ValidationError:
        pass


def test_happyhorse_rejects_invalid_resolution() -> None:
    from pydantic import ValidationError

    from src.models import HappyHorseParameters

    try:
        HappyHorseParameters(resolution="4k")
        assert False, "应拒绝 resolution=4k"
    except ValidationError:
        pass


def test_happyhorse_watermark_default_true() -> None:
    from src.models import HappyHorseParameters

    p = HappyHorseParameters()
    assert p.watermark is True, "HappyHorse 应默认带水印"


def test_happyhorse_watermark_false() -> None:
    from src.models import HappyHorseParameters

    p = HappyHorseParameters(watermark=False)
    assert p.watermark is False


def test_happyhorse_request_full() -> None:
    from src.models import HappyHorseParameters, HappyHorseRequest

    req = HappyHorseRequest(
        input={"prompt": "test video"},
        parameters=HappyHorseParameters(
            resolution="1080p",
            ratio="9:16",
            duration=10,
            watermark=False,
            seed=123,
        ),
    )
    assert req.model == "HappyHorse-1.0-T2V"
    dumped = req.model_dump(exclude_none=True)
    assert dumped["model"] == "HappyHorse-1.0-T2V"
    assert dumped["input"]["prompt"] == "test video"
    assert dumped["parameters"]["resolution"] == "1080p"
    assert dumped["parameters"]["ratio"] == "9:16"
    assert dumped["parameters"]["duration"] == 10
    assert dumped["parameters"]["watermark"] is False
    assert dumped["parameters"]["seed"] == 123


# ── Regression: Seedance still works ──────────────────────────────────


def test_seedance_regression_after_happyhorse() -> None:
    from pydantic import ValidationError

    from src.models import SeedanceParameters

    p = SeedanceParameters(resolution="480p", ratio="adaptive")
    assert p.resolution == "480p"
    assert p.ratio == "adaptive"

    try:
        SeedanceParameters(ratio="1:1")
        assert False, "Seedance 应拒绝 ratio=1:1"
    except ValidationError:
        pass

    p2 = SeedanceParameters()
    assert p2.watermark is False, "Seedance 应默认无 watermark"


# ── Wan2.7-T2V (万相) model ──────────────────────────────────────────


def test_wan_basic() -> None:
    from src.models import WanRequest

    req = WanRequest(input={"prompt": "a dog running"})
    assert req.model == "Wan2.7-T2V"
    assert req.input.prompt == "a dog running"
    assert req.parameters.resolution == "720p"
    assert req.parameters.ratio == "16:9"
    assert req.parameters.duration == 5
    assert req.parameters.watermark is False


def test_wan_accepts_valid_duration() -> None:
    from src.models import WanParameters

    for d in (2, 5, 10, 15):
        p = WanParameters(duration=d)
        assert p.duration == d


def test_wan_rejects_duration_below_2() -> None:
    from pydantic import ValidationError

    from src.models import WanParameters

    try:
        WanParameters(duration=1)
        assert False, "应拒绝 duration=1 (<2)"
    except ValidationError:
        pass


def test_wan_rejects_duration_above_15() -> None:
    from pydantic import ValidationError

    from src.models import WanParameters

    try:
        WanParameters(duration=16)
        assert False, "应拒绝 duration=16 (>15)"
    except ValidationError:
        pass


def test_wan_accepts_480p() -> None:
    from src.models import WanParameters

    p = WanParameters(resolution="480p")
    assert p.resolution == "480p"


def test_wan_accepts_720p_1080p() -> None:
    from src.models import WanParameters

    for r in ("720p", "1080p"):
        p = WanParameters(resolution=r)
        assert p.resolution == r


def test_wan_rejects_invalid_resolution() -> None:
    from pydantic import ValidationError

    from src.models import WanParameters

    try:
        WanParameters(resolution="4k")
        assert False, "应拒绝 resolution=4k"
    except ValidationError:
        pass


def test_wan_accepts_valid_ratios() -> None:
    from src.models import WanParameters

    for r in ("16:9", "9:16"):
        p = WanParameters(ratio=r)
        assert p.ratio == r


def test_wan_rejects_ratio_1_1() -> None:
    from pydantic import ValidationError

    from src.models import WanParameters

    try:
        WanParameters(ratio="1:1")
        assert False, "Wan 应拒绝 ratio=1:1"
    except ValidationError:
        pass


def test_wan_input_with_negative_prompt() -> None:
    from src.models import WanInput, WanRequest

    inp = WanInput(prompt="a cat", negative_prompt="blurry, low quality")
    assert inp.negative_prompt == "blurry, low quality"

    req = WanRequest(input=inp)
    dumped = req.model_dump(exclude_none=True)
    assert dumped["input"]["negative_prompt"] == "blurry, low quality"


def test_wan_input_with_audio_url() -> None:
    from src.models import WanInput

    inp = WanInput(prompt="dance", audio_url="https://example.com/music.mp3")
    assert inp.audio_url == "https://example.com/music.mp3"


def test_wan_parameters_with_prompt_extend() -> None:
    from src.models import WanParameters

    p = WanParameters(prompt_extend=True)
    assert p.prompt_extend is True

    dumped = p.model_dump(exclude_none=True)
    assert dumped["prompt_extend"] is True


def test_wan_request_full() -> None:
    from src.models import WanInput, WanParameters, WanRequest

    req = WanRequest(
        input=WanInput(prompt="test", negative_prompt="bad", audio_url="https://a.mp3"),
        parameters=WanParameters(
            resolution="1080p",
            ratio="9:16",
            duration=10,
            prompt_extend=True,
            watermark=False,
            seed=42,
        ),
    )
    dumped = req.model_dump(exclude_none=True)
    assert dumped["model"] == "Wan2.7-T2V"
    assert dumped["input"]["prompt"] == "test"
    assert dumped["input"]["negative_prompt"] == "bad"
    assert dumped["input"]["audio_url"] == "https://a.mp3"
    assert dumped["parameters"]["resolution"] == "1080p"
    assert dumped["parameters"]["ratio"] == "9:16"
    assert dumped["parameters"]["duration"] == 10
    assert dumped["parameters"]["prompt_extend"] is True
    assert dumped["parameters"]["watermark"] is False
    assert dumped["parameters"]["seed"] == 42


# ── Regression: all three models coexist ──────────────────────────────


def test_three_models_regression() -> None:
    from src.models import (
        HappyHorseRequest,
        SeedanceRequest,
        WanRequest,
    )

    s = SeedanceRequest(input={"prompt": "s"})
    assert s.model == "Seedance2.0"

    h = HappyHorseRequest(input={"prompt": "h"})
    assert h.model == "HappyHorse-1.0-T2V"

    w = WanRequest(input={"prompt": "w"})
    assert w.model == "Wan2.7-T2V"


# ── Qwen-Image-2.0 (千问) model ───────────────────────────────────────


def test_qwen_basic() -> None:
    from src.models import QwenImageRequest

    req = QwenImageRequest(input={"prompt": "a cat"})
    assert req.model == "Qwen-Image-2.0"
    assert req.input.prompt == "a cat"
    assert req.parameters.size == "2048*2048"
    assert req.parameters.n == 1
    assert req.parameters.prompt_extend is True
    assert req.parameters.watermark is False


def test_qwen_n_clamps_low() -> None:
    from src.models import QwenImageParameters

    p = QwenImageParameters(n=0)
    assert p.n == 1, "n 下限应截断到 1"


def test_qwen_n_clamps_high() -> None:
    from src.models import QwenImageParameters

    p = QwenImageParameters(n=10)
    assert p.n == 6, "n 上限应截断到 6"


def test_qwen_n_valid() -> None:
    from src.models import QwenImageParameters

    for n in (1, 3, 6):
        p = QwenImageParameters(n=n)
        assert p.n == n


def test_qwen_size_valid() -> None:
    from src.models import QwenImageParameters

    p = QwenImageParameters(size="2048*2048")
    assert p.size == "2048*2048"

    p2 = QwenImageParameters(size="1024*1024")
    assert p2.size == "1024*1024"


def test_qwen_size_too_small() -> None:
    from pydantic import ValidationError

    from src.models import QwenImageParameters

    try:
        QwenImageParameters(size="256*256")
        assert False, "应拒绝总像素 < 512*512"
    except ValidationError:
        pass


def test_qwen_size_too_big() -> None:
    from pydantic import ValidationError

    from src.models import QwenImageParameters

    try:
        QwenImageParameters(size="4096*4096")
        assert False, "应拒绝总像素 > 2048*2048"
    except ValidationError:
        pass


def test_qwen_negative_prompt() -> None:
    from src.models import QwenImageInput

    inp = QwenImageInput(prompt="a cat", negative_prompt="blurry")
    assert inp.negative_prompt == "blurry"


def test_qwen_prompt_extend_false() -> None:
    from src.models import QwenImageParameters

    p = QwenImageParameters(prompt_extend=False)
    assert p.prompt_extend is False

    dumped = p.model_dump(exclude_none=True)
    assert dumped["prompt_extend"] is False


def test_qwen_watermark_true() -> None:
    from src.models import QwenImageParameters

    p = QwenImageParameters(watermark=True)
    assert p.watermark is True


def test_qwen_request_full() -> None:
    from src.models import QwenImageInput, QwenImageParameters, QwenImageRequest

    req = QwenImageRequest(
        input=QwenImageInput(prompt="test", negative_prompt="bad"),
        parameters=QwenImageParameters(
            size="1536*2688",
            n=2,
            prompt_extend=False,
            watermark=True,
            seed=7,
        ),
    )
    dumped = req.model_dump(exclude_none=True)
    assert dumped["model"] == "Qwen-Image-2.0"
    assert dumped["input"]["prompt"] == "test"
    assert dumped["input"]["negative_prompt"] == "bad"
    assert dumped["parameters"]["size"] == "1536*2688"
    assert dumped["parameters"]["n"] == 2
    assert dumped["parameters"]["prompt_extend"] is False
    assert dumped["parameters"]["watermark"] is True
    assert dumped["parameters"]["seed"] == 7


# ── Regression: Agnes ImageRequest still works ────────────────────────


def test_image_request_regression() -> None:
    from src.models import ImageRequest

    req = ImageRequest(prompt="a cat", size="1024x768")
    assert req.model == "agnes-image-2.1-flash"
    assert req.size == "1024x768"
