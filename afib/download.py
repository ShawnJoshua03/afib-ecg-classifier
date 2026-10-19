"""Download the public training set, validate byte ranges, and extract safely."""

import argparse
import hashlib
import json
import shutil
import time
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE_URL = "https://physionet.org/files/challenge-2017/1.0.0/"
ARCHIVE_BYTES = 99_226_822
# Measured from the first complete CRC-validated download; enforced on reproduction.
ARCHIVE_SHA256 = "25fdbab36bb6724b66a4d2c26ff89f6b9d6ff87e6aed714d24cf5bf071cd1255"
REFERENCE_SHA256 = "ae517e474b0bc89a7517ad876b5b4dadc6c94f680d0665c04746db9432df855b"


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def download(raw_dir=Path("data/raw"), workers=8):
    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    archive = raw_dir / "training2017.zip"
    if not archive.exists() or archive.stat().st_size != ARCHIVE_BYTES:
        url = BASE_URL + archive.name
        request = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(request, timeout=60) as response:
            size = int(response.headers["Content-Length"])
        print(f"Archive size before download: {size:,} bytes", flush=True)
        if size != ARCHIVE_BYTES:
            raise ValueError(f"Archive changed: expected {ARCHIVE_BYTES}, got {size}")
        chunk_size = 4 * 1024 * 1024
        starts = list(range(0, size, chunk_size))

        def fetch(start):
            end = min(start + chunk_size, size) - 1
            chunk = raw_dir / f"archive.part-{start}"
            for attempt in range(3):
                try:
                    req = urllib.request.Request(url, headers={"Range": f"bytes={start}-{end}"})
                    with urllib.request.urlopen(req, timeout=120) as response:
                        expected_range = f"bytes {start}-{end}/{size}"
                        if response.headers.get("Content-Range") != expected_range:
                            raise ValueError("Server did not honor the requested byte range")
                        with chunk.open("wb") as stream:
                            shutil.copyfileobj(response, stream)
                    if chunk.stat().st_size != end - start + 1:
                        raise ValueError("Truncated download chunk")
                    print(f"Downloaded bytes {start}-{end}", flush=True)
                    return chunk
                except (OSError, ValueError):
                    if attempt == 2:
                        raise
                    time.sleep(2**attempt)
            raise RuntimeError("Unreachable retry state")

        with ThreadPoolExecutor(max_workers=workers) as pool:
            chunks = list(pool.map(fetch, starts))
        temporary = raw_dir / "training2017.complete.tmp"
        with temporary.open("wb") as target:
            for chunk in chunks:
                with chunk.open("rb") as source:
                    shutil.copyfileobj(source, target)
        temporary.replace(archive)
        for chunk in chunks:
            chunk.unlink()
    archive_hash = sha256(archive)
    if ARCHIVE_SHA256 and archive_hash != ARCHIVE_SHA256:
        raise ValueError("Training archive SHA-256 does not match the frozen source")
    with zipfile.ZipFile(archive) as zipped:
        root = raw_dir.resolve()
        for name in zipped.namelist():
            if not (root / name).resolve().is_relative_to(root):
                raise ValueError("Unsafe archive member")
        bad_member = zipped.testzip()
        if bad_member:
            raise ValueError(f"Archive CRC failed: {bad_member}")
        zipped.extractall(raw_dir)
        uncompressed = sum(info.file_size for info in zipped.infolist())
    reference = raw_dir / "REFERENCE-v3.csv"
    if not reference.exists():
        urllib.request.urlretrieve(BASE_URL + reference.name, reference)
    reference_hash = sha256(reference)
    if REFERENCE_SHA256 and reference_hash != REFERENCE_SHA256:
        raise ValueError("Final reference labels SHA-256 does not match the frozen source")
    provenance = {
        "archive_url": BASE_URL + archive.name,
        "archive_bytes": archive.stat().st_size,
        "archive_sha256": archive_hash,
        "uncompressed_bytes": uncompressed,
        "reference_url": BASE_URL + reference.name,
        "reference_sha256": reference_hash,
        "license": "Open Data Commons Attribution License v1.0",
    }
    (raw_dir / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    print(json.dumps(provenance, indent=2), flush=True)
    return provenance


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    download(args.raw_dir, args.workers)
