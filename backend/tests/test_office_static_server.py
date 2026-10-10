"""Word ribbon images must be cacheable while frontend code stays fresh."""

import threading
from functools import partial
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen

import pytest

from gui.views.office_install_interface import OfficeStaticRequestHandler


@pytest.fixture
def static_server(tmp_path):
    resources = ["icon.png", "icon.svg", "image.jpg", "taskpane.html", "dialog.js", "style.css", "manifest.xml", "settings.json"]
    for name in resources:
        (tmp_path / name).write_bytes(b"test resource")
    handler = partial(OfficeStaticRequestHandler, directory=str(tmp_path))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@pytest.mark.parametrize("path, content_type", [
    ("icon.png", "image/png"),
    ("icon.png?v=2", "image/png"),
    ("icon.svg", "image/svg+xml"),
    ("image.jpg", "image/jpeg"),
])
@pytest.mark.parametrize("method", ["GET", "HEAD"])
def test_image_responses_allow_office_caching(static_server, path, content_type, method):
    with urlopen(Request(f"{static_server}/{path}", method=method), timeout=2) as response:
        assert response.status == 200
        assert response.headers["Content-Type"] == content_type
        assert response.headers["Access-Control-Allow-Origin"] == "*"
        for header in ("Cache-Control", "Pragma", "Expires"):
            assert header not in response.headers


@pytest.mark.parametrize("path", ["taskpane.html", "dialog.js?v=2", "style.css", "manifest.xml", "settings.json"])
def test_frontend_code_and_manifest_still_disable_caching(static_server, path):
    with urlopen(f"{static_server}/{path}", timeout=2) as response:
        assert response.status == 200
        assert response.headers["Cache-Control"] == "no-cache, no-store, must-revalidate"
        assert response.headers["Pragma"] == "no-cache"
        assert response.headers["Expires"] == "0"
        assert response.headers["Access-Control-Allow-Origin"] == "*"
