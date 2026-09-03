from leitor_lote.models import PreparedImage, Reading, Tipo


class FakeReader:
    id = "fake"
    requer_chave = False

    def __init__(self, valor: str = "349498", confianca: float | None = 0.9, falhar: bool = False):
        self._valor = valor
        self._conf = confianca
        self._falhar = falhar

    def disponivel(self, config) -> bool:
        return True

    def read(self, imagem: PreparedImage, tipo: Tipo) -> Reading:
        if self._falhar:
            raise RuntimeError("boom")
        return Reading(valor=self._valor, confianca=self._conf, motor="fake", bruto=self._valor)
