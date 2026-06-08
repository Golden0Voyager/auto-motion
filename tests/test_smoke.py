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
        v = VideoCreateRequest(prompt="x", num_frames=n)
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
