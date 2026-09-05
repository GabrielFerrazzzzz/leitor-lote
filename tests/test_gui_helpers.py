from leitor_lote import gui
from leitor_lote.config import Config


def test_opcoes_motor_ocr_so_locais():
    ids = [m for m, _ in gui.opcoes_motor("ocr", Config())]
    assert ids == ["tesseract", "rapidocr", "trocr"]


def test_opcoes_motor_ia_desabilita_sem_chave():
    opts = gui.opcoes_motor("ia", Config())
    assert opts and all(habil is False for _, habil in opts)
    opts2 = gui.opcoes_motor("ia", Config(chave_openai="sk"))
    assert ("openai:gpt-5-mini", True) in opts2
    assert ("mistral-ocr", False) in opts2


def test_montar_parametros_vazios_viram_none(tmp_path):
    p = gui.montar_parametros(str(tmp_path), "canhoto", "rapidocr", "auto", "", "  ")
    assert p.seq_esperada is None
    assert p.intervalo_maximo is None
    p2 = gui.montar_parametros(str(tmp_path), "canhoto", "rapidocr", "auto", "383400", "1000")
    assert (p2.seq_esperada, p2.intervalo_maximo) == (383400, 1000)


def test_montar_parametros_motor_fallback(tmp_path):
    p = gui.montar_parametros(str(tmp_path), "canhoto", "rapidocr", "ocr", "", "")
    assert p.motor_fallback is None
    p2 = gui.montar_parametros(str(tmp_path), "canhoto", "rapidocr", "ocr", "", "", "trocr")
    assert p2.motor_fallback == "trocr"
    p3 = gui.montar_parametros(str(tmp_path), "canhoto", "rapidocr", "ocr", "", "", "")
    assert p3.motor_fallback is None  # string vazia vira None
