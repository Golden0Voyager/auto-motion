from __future__ import annotations

from unittest.mock import patch


def test_web_imports() -> None:
    from web import app
    assert app is not None
    assert app.name == "web"


def test_index_route() -> None:
    from web import app
    with app.test_client() as c:
        resp = c.get("/")
        assert resp.status_code == 200
        assert b"auto_motion" in resp.data


def test_templates_route() -> None:
    from web import app
    with app.test_client() as c:
        resp = c.get("/api/templates")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "templates" in data
        assert len(data["templates"]) >= 16


def test_templates_structure() -> None:
    from web import app
    with app.test_client() as c:
        resp = c.get("/api/templates")
        data = resp.get_json()
        t = data["templates"][0]
        assert set(t.keys()) == {"id", "category", "icon", "name", "desc", "template", "params"}
        assert "model" in t["params"]
        assert "size" in t["params"]


def test_optimize_missing_subject() -> None:
    from web import app
    with app.test_client() as c:
        resp = c.post("/api/optimize", json={})
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data


def test_optimize_invalid_template() -> None:
    from web import app
    with app.test_client() as c:
        resp = c.post("/api/optimize", json={
            "template_id": "nonexistent",
            "subject": "test",
        })
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data


@patch("web._download_and_save", return_value="/output/fake.png")
@patch("web._sensenova_generate_image", return_value="https://fake.url/img.png")
@patch("web._expand_prompt", return_value="expanded prompt for a young woman")
def test_optimize_with_template(mock_expand, mock_generate, mock_download) -> None:
    """使用模版时正常返回扩写+生成结果（不调真实 API）"""
    from web import app
    with app.test_client() as c:
        resp = c.post("/api/optimize", json={
            "template_id": "portrait_01",
            "subject": "a young woman",
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["original"] == "a young woman"
        assert "expanded" in data
        assert data["params"]["model"] == "sensenova-u1-fast"
        assert data["params"]["size"] == "2048x2048"
        assert data["url"] == "/output/fake.png"
        assert data["model_used"] == "sensenova-u1-fast"


@patch("web._download_and_save", return_value="/output/fake.png")
@patch("web._sensenova_generate_image", return_value="https://fake.url/img.png")
@patch("web._expand_prompt", return_value="expanded prompt for a young woman")
def test_optimize_model_override(mock_expand, mock_generate, mock_download) -> None:
    """用户传递 model 参数时覆盖模版默认值"""
    from web import app
    with app.test_client() as c:
        resp = c.post("/api/optimize", json={
            "template_id": "portrait_01",
            "subject": "a young woman",
            "model": "agnes-image-2.1-flash",
            "size": "1024x768",
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["params"]["model"] == "agnes-image-2.1-flash"
        assert data["params"]["size"] == "1024x768"
        assert data["model_used"] == "agnes-image-2.1-flash"


@patch("web._download_and_save", return_value="/output/fake.png")
@patch("web._sensenova_generate_image", return_value="https://fake.url/img.png")
@patch("web._expand_prompt", return_value="A cat on a mat")
def test_optimize_custom_prompt(mock_expand, mock_generate, mock_download) -> None:
    """custom_prompt 优先级高于模版"""
    from web import app
    with app.test_client() as c:
        resp = c.post("/api/optimize", json={
            "template_id": "portrait_01",
            "subject": "test",
            "custom_prompt": "A cat on a mat",
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert "cat" in data["expanded"]


@patch("web._download_and_save", return_value="/output/fake.png")
@patch("web._sensenova_generate_image", side_effect=RuntimeError("API 配额用尽"))
@patch("web._expand_prompt", return_value="expanded prompt")
def test_optimize_generate_error(mock_expand, mock_generate, mock_download) -> None:
    """生成阶段报错时返回 502 + 错误详情"""
    from web import app
    with app.test_client() as c:
        resp = c.post("/api/optimize", json={
            "template_id": "portrait_01",
            "subject": "test",
        })
        assert resp.status_code == 502
        data = resp.get_json()
        assert "error" in data
        assert "API 配额用尽" in data["error"]
