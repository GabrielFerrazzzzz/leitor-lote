from __future__ import annotations

import io
import tempfile
from pathlib import Path

import cv2
import numpy as np
import pypdfium2 as pdfium
from PIL import Image, ImageOps

from leitor_lote.models import PreparedImage

MAX_LADO = 2000
JPEG_Q = 82
DPI = 300


def _deskew(arr: np.ndarray) -> np.ndarray:
    coords = np.column_stack(np.where(arr < 255))
    if coords.size == 0:
        return arr
    angle = cv2.minAreaRect(coords.astype(np.float32))[-1]
    angle = -(90 + angle) if angle < -45 else -angle
    if abs(angle) < 0.5:
        return arr
    h, w = arr.shape
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(arr, m, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def _para_prepared(img: Image.Image, para_ocr: bool) -> PreparedImage:
    img = ImageOps.exif_transpose(img).convert("RGB")
    if max(img.size) > MAX_LADO:
        img.thumbnail((MAX_LADO, MAX_LADO))
    if para_ocr:
        arr = np.array(img.convert("L"))
        arr = cv2.adaptiveThreshold(
            arr, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 10
        )
        arr = _deskew(arr)
        saida = Image.fromarray(arr).convert("RGB")
    else:
        saida = img
    buf = io.BytesIO()
    saida.save(buf, format="JPEG", quality=JPEG_Q)
    dados = buf.getvalue()
    fd, nome = tempfile.mkstemp(suffix=".jpg")
    tmp = Path(nome)
    with open(fd, "wb") as f:
        f.write(dados)
    return PreparedImage(
        bytes_=dados,
        mimetype="image/jpeg",
        largura=saida.width,
        altura=saida.height,
        caminho_tmp=tmp,
    )


def preparar(arquivo: Path, *, para_ocr: bool) -> list[PreparedImage]:
    if arquivo.suffix.lower() == ".pdf":
        doc = pdfium.PdfDocument(str(arquivo))
        try:
            return [
                _para_prepared(doc[i].render(scale=DPI / 72).to_pil(), para_ocr)
                for i in range(len(doc))
            ]
        finally:
            doc.close()
    with Image.open(arquivo) as img:
        return [_para_prepared(img, para_ocr)]
