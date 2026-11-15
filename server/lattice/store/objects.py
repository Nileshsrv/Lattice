"""Content-addressed object store (local-directory backend; S3-swappable seam #3).

Objects are immutable: a hash collision with different content is an integrity
failure (I-1), never an overwrite.
"""

import hashlib
from pathlib import Path

from .. import config


def _path_for(sha: str) -> Path:
    return config.OBJECTS_DIR / sha[:2] / sha


def put(content: bytes) -> str:
    sha = hashlib.sha256(content).hexdigest()
    path = _path_for(sha)
    if path.exists():
        existing = path.read_bytes()
        if existing != content:
            raise RuntimeError(f"object store integrity failure for {sha}")
        return sha
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(content)
    tmp.replace(path)
    return sha


def get(sha: str) -> bytes:
    content = _path_for(sha).read_bytes()
    actual = hashlib.sha256(content).hexdigest()
    if actual != sha:
        raise RuntimeError(f"object store corruption: expected {sha}, got {actual}")
    return content


def exists(sha: str) -> bool:
    return _path_for(sha).exists()
