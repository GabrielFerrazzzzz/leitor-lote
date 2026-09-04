from pathlib import Path

from leitor_lote import output
from leitor_lote.models import LinhaResultado


def test_limpar_nome():
    assert output.limpar_nome("São Paulo 12!") == "SAO_PAULO_12"
    assert output.limpar_nome("---") == "SEM_LEITURA"


def _entrada(tmp_path: Path, nomes: list[str]) -> Path:
    d = tmp_path / "entrada"
    d.mkdir()
    for n in nomes:
        (d / n).write_bytes(b"conteudo")
    return d


def test_copiar_arquivos_renomeia_com_texto_lido(tmp_path):
    ent = _entrada(tmp_path, ["a.jpg"])
    linhas = [LinhaResultado("a.jpg", "349498", 0.91, "rapidocr", "ok", None)]
    output.copiar_arquivos(linhas, ent / "saida")
    assert (ent / "saida" / "349498.jpg").exists()


def test_colisao_ganha_sufixo(tmp_path):
    ent = _entrada(tmp_path, ["a.jpg", "b.jpg"])
    linhas = [
        LinhaResultado("a.jpg", "Não reconhecido", None, "rapidocr", "nao_reconhecido", None),
        LinhaResultado("b.jpg", "Não reconhecido", None, "rapidocr", "nao_reconhecido", None),
    ]
    output.copiar_arquivos(linhas, ent / "saida")
    assert (ent / "saida" / "NAO_RECONHECIDO.jpg").exists()
    assert (ent / "saida" / "NAO_RECONHECIDO_2.jpg").exists()


def test_erro_ganha_prefixo(tmp_path):
    ent = _entrada(tmp_path, ["falha.jpg"])
    linhas = [LinhaResultado("falha.jpg", "", None, "", "erro", "timeout")]
    output.copiar_arquivos(linhas, ent / "saida")
    assert (ent / "saida" / "ERRO_FALHA.jpg").exists()


def test_copiar_arquivos_nao_grava_csv_nem_log(tmp_path):
    ent = _entrada(tmp_path, ["a.jpg"])
    linhas = [LinhaResultado("a.jpg", "349498", 0.91, "rapidocr", "ok", None)]
    output.copiar_arquivos(linhas, ent / "saida")
    assert not (ent / "saida" / "resultado.csv").exists()
    assert not (ent / "saida" / "log.txt").exists()


def test_exportar_csv_com_bom_e_cabecalho(tmp_path):
    linhas = [LinhaResultado("a.jpg", "349498", 0.91, "rapidocr", "ok", None)]
    destino = tmp_path / "resultado.csv"
    output.exportar_csv(linhas, destino)
    csv_bytes = destino.read_bytes()
    assert csv_bytes[:3] == b"\xef\xbb\xbf"
    header = csv_bytes.decode("utf-8-sig").splitlines()[0]
    assert header == "arquivo,texto_lido,confianca,motor,status,erro"


def test_exportar_csv_em_caminho_arbitrario_fora_da_pasta_saida(tmp_path):
    linhas = [LinhaResultado("a.jpg", "349498", 0.91, "rapidocr", "ok", None)]
    destino = tmp_path / "relatorios" / "export-cliente.csv"
    output.exportar_csv(linhas, destino)
    assert destino.exists()
    assert destino.read_text("utf-8-sig").splitlines()[0] == (
        "arquivo,texto_lido,confianca,motor,status,erro"
    )


def test_csv_nao_tem_colunas_de_chave(tmp_path):
    destino = tmp_path / "resultado.csv"
    output.exportar_csv([LinhaResultado("a.jpg", "1", None, "openai:gpt-5", "ok", None)], destino)
    header = destino.read_text("utf-8-sig").splitlines()[0]
    assert "chave" not in header and "key" not in header.lower()
