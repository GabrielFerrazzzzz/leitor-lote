# leitor-lote.spec
import shutil

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = [("leitor_lote/tipos.fallback.json", "leitor_lote")]
datas += collect_data_files("rapidocr_onnxruntime")  # modelos .onnx + config.yaml
datas += collect_data_files("pypdfium2_raw")

binaries = []
_tess = shutil.which("tesseract")
if _tess:
    binaries.append((_tess, "."))

hiddenimports = (
    collect_submodules("rapidocr_onnxruntime")
    + collect_submodules("onnxruntime")
    + ["PIL._tkinter_finder"]
)

a = Analysis(
    ["leitor_lote/__main__.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="leitor-lote", console=False)
coll = COLLECT(exe, a.binaries, a.datas, name="leitor-lote")
