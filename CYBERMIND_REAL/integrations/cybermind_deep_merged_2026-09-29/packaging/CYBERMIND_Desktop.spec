# Build with: .desktop-venv\Scripts\pyinstaller.exe --noconfirm packaging\CYBERMIND_Desktop.spec
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules
import torch_geometric

root = Path(SPECPATH).parent
datas = [
    (str(root / "frontend" / "dist"), "frontend/dist"),
    (str(root / "models" / "best.pt"), "models"),
    (str(root / "results" / "final_grouped_model_comparison.json"), "results"),
    (str(root / "knowledge" / "stage_mapping.yaml"), "knowledge"),
    (str(root / "data" / "test_cases"), "data/test_cases"),
    (str(root / "examples" / "test_cases"), "examples/test_cases"),
    (str(root / "tools" / "incident_decrypter" / "index.html"), "tools/incident_decrypter"),
]
# TorchScript inspects PyG class source during import; bytecode alone is not
# sufficient for the selected GATv2 checkpoint.
pyg_root = Path(torch_geometric.__file__).parent
datas += [
    (str(source), str(Path("torch_geometric") / source.relative_to(pyg_root).parent))
    for source in pyg_root.rglob("*.py")
]
hiddenimports = [
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.lifespan.on",
    "scapy.all",
] + collect_submodules("torch_geometric")

a = Analysis(
    [str(root / "packaging" / "desktop_app.py")],
    pathex=[str(root), str(root / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "notebook", "jupyter", "IPython", "pytest"],
    noarchive=False,
)
# Qt6Core needs Windows' unversioned system ICU exports. A different ICU DLL
# discovered through other packages shadows it and breaks QtCore at import.
a.binaries = [entry for entry in a.binaries if Path(entry[0]).name.lower() != "icuuc.dll"]
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CYBERMIND",
    console=False,
    disable_windowed_traceback=False,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="CYBERMIND_DESKTOP")
