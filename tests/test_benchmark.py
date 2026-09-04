from PIL import Image

from bench import benchmark
from leitor_lote.models import Campo, Reading, Tipo

_TIPO_TESTE = Tipo(id="canhoto", nome="Canhoto", prompt="", modo="ocr", motor="fake",
                   campos=(Campo("numero", 6),))


def test_lev():
    assert benchmark.lev("123", "123") == 0
    assert benchmark.lev("123", "124") == 1
    assert benchmark.lev("", "12") == 2


def test_cer_digitos():
    assert benchmark.cer_digitos("383462", "383462") == 0.0
    assert abs(benchmark.cer_digitos("383462", "383460") - (1 / 6)) < 1e-9


def test_rodar_com_fake(tmp_path, monkeypatch):
    pasta = tmp_path / "amostras"
    pasta.mkdir()
    for n in ("a.jpg", "b.jpg"):
        Image.new("RGB", (40, 40), "white").save(pasta / n)
    gab = pasta / "gabarito.csv"
    gab.write_text("arquivo,esperado\na.jpg,349498\nb.jpg,111111\n", encoding="utf-8-sig")

    monkeypatch.setattr(benchmark, "preparar",
                        lambda *a, **k: [object()])

    class _R:
        def read(self, img, tipo):
            return Reading(valor="349498", confianca=None, motor="fake", bruto="")

    monkeypatch.setattr(benchmark, "resolve", lambda mid, cfg: _R())
    monkeypatch.setattr(benchmark, "_tipo", lambda tid: _TIPO_TESTE)
    linhas = benchmark.rodar(pasta, gab, "canhoto", ["fake"])
    assert linhas[0]["motor"] == "fake"
    assert linhas[0]["acerto_%"] == 50.0
    assert linhas[0]["nao_reconhecido"] == 0
