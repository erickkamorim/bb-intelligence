"""Download bruto versionado e idempotente.

Arquivos vão para data/raw/<fonte>/<AAAA-MM-DD>/<nome>. Se o SHA-256 for igual ao
último download da mesma URL, o novo arquivo é descartado e o anterior reaproveitado.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class RawFile:
    path: Path
    url: str
    sha256: str
    retrieved_at: datetime
    reused: bool


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _manifest(root: Path) -> Path:
    return root / "manifest.jsonl"


def last_entry(root: Path, url: str) -> dict | None:
    m = _manifest(root)
    if not m.exists():
        return None
    last = None
    for line in m.read_text(encoding="utf-8").splitlines():
        e = json.loads(line)
        if e["url"] == url:
            last = e
    return last


def download(url: str, root: Path, source_code: str, session=None, timeout: float = 120.0) -> RawFile:
    import requests

    now = datetime.now(timezone.utc)
    target_dir = root / source_code / now.strftime("%Y-%m-%d")
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / url.rstrip("/").split("/")[-1].split("?")[0]
    tmp = target.with_suffix(target.suffix + ".part")

    s = session or requests.Session()
    with s.get(url, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        with open(tmp, "wb") as fh:
            for chunk in r.iter_content(1 << 20):
                fh.write(chunk)
    digest = sha256_file(tmp)

    prev = last_entry(root, url)
    if prev and prev["sha256"] == digest and Path(prev["path"]).exists():
        tmp.unlink()
        return RawFile(Path(prev["path"]), url, digest, datetime.fromisoformat(prev["retrieved_at"]), True)

    tmp.replace(target)
    entry = {"url": url, "path": str(target), "sha256": digest, "retrieved_at": now.isoformat(),
             "source": source_code}
    with open(_manifest(root), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    return RawFile(target, url, digest, now, False)
