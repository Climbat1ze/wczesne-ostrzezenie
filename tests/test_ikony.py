import json

from PIL import Image

import ikony


def test_ikony_i_manifest(tmp_path):
    pliki = ikony.zapisz(tmp_path)
    assert "manifest.webmanifest" in pliki
    m = json.loads((tmp_path / "manifest.webmanifest").read_text(encoding="utf-8"))
    assert m["display"] == "standalone" and m["start_url"] == "./"
    rozm = {i["sizes"] for i in m["icons"]}
    assert {"192x192", "512x512"} <= rozm and any(i["purpose"] == "maskable" for i in m["icons"])
    for i in m["icons"]:
        w, h = Image.open(tmp_path / i["src"]).size
        assert f"{w}x{h}" == i["sizes"]
    assert Image.open(tmp_path / "apple-touch-icon.png").size == (180, 180)


def test_glowa_strony():
    assert 'rel="manifest"' in ikony.GLOWA and 'rel="apple-touch-icon"' in ikony.GLOWA
