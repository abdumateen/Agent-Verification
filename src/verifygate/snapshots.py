"""Immutable-by-convention copies and content fingerprints of candidates."""

import hashlib
import os
from pathlib import Path
import shutil
import stat


_EXCLUDED = {".git", "__pycache__", ".verifygate"}


def _files(root: Path) -> list[tuple[str, Path]]:
    if not root.is_dir() or root.is_symlink():
        raise ValueError("snapshot source must be a real directory")
    found = []

    def visit(directory: Path) -> None:
        for entry in directory.iterdir():
            if entry.name in _EXCLUDED:
                continue
            mode = entry.lstat().st_mode
            if stat.S_ISDIR(mode):
                visit(entry)
            elif stat.S_ISREG(mode):
                found.append((entry.relative_to(root).as_posix(), entry))
            else:
                raise ValueError(f"unsupported candidate entry: {entry}")

    visit(root)
    return sorted(found)


def fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    for name, file in _files(path):
        content = file.read_bytes()
        encoded = name.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def create_snapshot(src: Path, dst: Path) -> str:
    source = src.resolve(strict=True)
    destination = dst.resolve()
    if destination == source or source in destination.parents:
        raise ValueError("snapshot destination must be outside candidate")
    if dst.exists() or dst.is_symlink():
        raise ValueError("snapshot destination already exists")
    files = _files(src)  # Validate the complete tree before creating anything.
    dst.mkdir(parents=True)
    try:
        for name, file in files:
            target = dst.joinpath(*name.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(file, target, follow_symlinks=False)
        return fingerprint(dst)
    except BaseException:
        shutil.rmtree(dst)
        raise
