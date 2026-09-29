# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

root = Path(SPECPATH)
a = Analysis(
    [str(root / "docker_desktop_launcher.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["torch", "torch_geometric", "matplotlib", "pytest"],
    noarchive=False,
)
# Avoid a conflicting ICU DLL shadowing the Windows system exports for Qt.
a.binaries = [entry for entry in a.binaries if Path(entry[0]).name.lower() != "icuuc.dll"]
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="CYBERMIND", console=False, upx=False,
    disable_windowed_traceback=False,
)
