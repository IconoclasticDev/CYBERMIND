"""Create a short-path, self-contained Windows desktop folder.

The Qt Quick QML theme assets are unused by the QWidget/WebEngine desktop
shell, but their deep filenames can exceed Explorer's legacy extraction limit.
Torch's nested license notices are retained in a flat text file.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="Tested onedir release folder")
    parser.add_argument("output", type=Path, help="New directly runnable release folder")
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    folder = args.output.resolve()
    if not (source / "CYBERMIND.exe").is_file():
        parser.error("source must contain CYBERMIND.exe")
    if not (source / "_internal").is_dir():
        parser.error("source must contain _internal")
    if folder.exists():
        parser.error("release folder already exists")
    folder.parent.mkdir(parents=True, exist_ok=True)

    def ignore(directory: str, names: list[str]) -> set[str]:
        parent = Path(directory)
        omitted: set[str] = set()
        if parent == source / "_internal" / "PySide6":
            omitted.add("qml")
        if parent == source / "_internal" / "torch-2.14.0.dist-info":
            omitted.add("licenses")
        if parent == source:
            # A previous extraction test was accidentally nested in this tree.
            omitted.add(source.name)
        return omitted.intersection(names)

    shutil.copytree(source, folder, dirs_exist_ok=True, ignore=ignore)
    licenses = source / "_internal" / "torch-2.14.0.dist-info" / "licenses"
    if licenses.is_dir():
        with (folder / "THIRD_PARTY_NOTICES.txt").open("w", encoding="utf-8") as notices:
            for item in sorted(licenses.rglob("*")):
                if item.is_file():
                    notices.write("\n\n" + "=" * 80 + "\n")
                    notices.write(item.relative_to(licenses).as_posix() + "\n")
                    notices.write("=" * 80 + "\n")
                    notices.write(item.read_text(encoding="utf-8", errors="replace"))

    readme = folder / "README_DESKTOP.md"
    if not readme.exists():
        shutil.copy2(Path(__file__).with_name("README_DESKTOP.md"), readme)
    readme.write_text(
        readme.read_text(encoding="utf-8").replace("`CYBERMIND_DESKTOP`", "`CYBERMIND`")
        + "\nThis folder is self-contained. Keep CYBERMIND.exe and _internal together. "
        + "THIRD_PARTY_NOTICES.txt contains bundled third-party notices. "
        + "The unused Qt Quick theme assets were omitted to keep extraction paths short.\n",
        encoding="utf-8",
    )

    files = sorted(item for item in folder.rglob("*") if item.is_file())
    max_path = max(len(item.relative_to(folder).as_posix()) for item in files)
    if max_path > 120:
        raise RuntimeError(f"runtime path is still too long: {max_path}")
    print(f"release_folder={folder}")
    print(f"release_files={len(files)}")
    print(f"max_relative_path={max_path}")
    print(f"exe_sha256={sha256(folder / 'CYBERMIND.exe')}")
    print(f"model_sha256={sha256(folder / '_internal' / 'models' / 'best.pt')}")


if __name__ == "__main__":
    main()
