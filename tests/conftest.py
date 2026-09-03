from pathlib import Path

import pytest
from PIL import Image


@pytest.fixture
def png_pequeno(tmp_path: Path) -> Path:
    p = tmp_path / "peq.png"
    Image.new("RGB", (100, 200), "white").save(p)
    return p


@pytest.fixture
def png_grande(tmp_path: Path) -> Path:
    p = tmp_path / "gr.png"
    Image.new("RGB", (3000, 2000), "white").save(p)
    return p


@pytest.fixture
def pdf_2p(tmp_path: Path) -> Path:
    p = tmp_path / "doc.pdf"
    a = Image.new("RGB", (400, 300), "white")
    b = Image.new("RGB", (400, 300), "gray")
    a.save(p, save_all=True, append_images=[b])
    return p
