"""Immutable-by-convention copies and content fingerprints of candidates."""

import hashlib
import os
from pathlib import Path
import shutil
import stat
import fnmatch


_EXCLUDED = {".git", ".venv", "venv", "__pycache__", ".verifygate", ".env", ".env.local", ".env.production", "secrets", ".secrets", "id_rsa", "id_ed25519"}
_PATTERNS = ("*.pem", "*.key", "*.p12", "*.pfx", ".env.*")


def _inventory(root: Path, exclusions=()) -> tuple[list[tuple[str, Path]], list[str]]:
    if not root.is_dir() or root.is_symlink():
        raise ValueError("snapshot source must be a real directory")
    found = []
    excluded = []

    def visit(directory: Path) -> None:
        for entry in directory.iterdir():
            relative = entry.relative_to(root).as_posix()
            if entry.name in _EXCLUDED or any(fnmatch.fnmatchcase(entry.name, pattern) for pattern in _PATTERNS) or any(fnmatch.fnmatchcase(relative, pattern) or fnmatch.fnmatchcase(entry.name, pattern) for pattern in exclusions):
                excluded.append(relative)
                continue
            mode = entry.lstat().st_mode
            if stat.S_ISDIR(mode):
                visit(entry)
            elif stat.S_ISREG(mode):
                found.append((relative, entry))
            else:
                raise ValueError(f"unsupported candidate entry: {relative}")

    visit(root)
    return sorted(found), sorted(excluded)


def _files(root: Path) -> list[tuple[str, Path]]:
    return _inventory(root)[0]


def manifest(root: Path, exclusions=()) -> dict:
    """List included and excluded relative paths, without file contents."""
    files, excluded = _inventory(root, exclusions)
    return {"files": [name for name, _ in files], "excluded_paths": excluded}


def fingerprint(path: Path, exclusions=()) -> str:
    digest = hashlib.sha256()
    for name, file in _inventory(path, exclusions)[0]:
        content = file.read_bytes()
        encoded = name.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def create_snapshot(src: Path, dst: Path, exclusions=()) -> str:
    source = src.resolve(strict=True)
    destination = dst.resolve()
    if destination == source or source in destination.parents:
        raise ValueError("snapshot destination must be outside candidate")
    if dst.exists() or dst.is_symlink():
        raise ValueError("snapshot destination already exists")
    files = _inventory(src, exclusions)[0]  # Validate the complete tree before creating anything.
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
