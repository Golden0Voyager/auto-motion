from __future__ import annotations


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
        assert len(data["templates"]) >= 8


def test_templates_structure() -> None:
    from web import app
    with app.test_client() as c:
        resp = c.get("/api/templates")
        data = resp.get_json()
        t = data["templates"][0]
        assert set(t.keys()) == {"id", "category", "icon", "name", "desc", "template", "params"}
        assert "model" in t["params"]
        assert "size" in t["params"]
