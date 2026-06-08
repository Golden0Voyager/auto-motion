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
