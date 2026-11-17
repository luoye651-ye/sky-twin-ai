"""Download the versioned public Ningbo dataset; resume, size + MD5 verification.

No dataset images/annotations are rewritten by this command. The archive and
publisher metadata are retained for provenance. MD5 is publisher integrity, not
a substitute for trusting the publisher; SHA-256 is recorded locally too.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.figshare.com/v2/articles/24123666/versions/2"
FILE_ID = 42321027
SIZE = 3189416277
MD5 = "1fc37cddddf9cf5d35d6363acd2b5f1e"


def hashes(path: Path) -> tuple[str, str]:
    md5, sha = hashlib.md5(), hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            md5.update(block)
            sha.update(block)
    return md5.hexdigest(), sha.hexdigest()


def main() -> None:
    folder = ROOT / "data/raw/ningbo-v2"
    folder.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(API, headers={"User-Agent": "SkyTwin-dataset-setup/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        metadata = json.load(response)
    entry = next(item for item in metadata["files"] if item["id"] == FILE_ID)
    if entry["size"] != SIZE or entry["computed_md5"] != MD5:
        raise RuntimeError("Publisher metadata changed; inspect before downloading.")
    (folder / "figshare-metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    target = folder / "river-floating-debris-v2.zip"
    partial = target.with_suffix(".zip.part")
    if not target.exists():
        for attempt in range(1, 9):
            offset = partial.stat().st_size if partial.exists() else 0
            if offset == SIZE:
                break
            if offset > SIZE:
                raise RuntimeError("Partial download exceeds expected size; preserve it and inspect manually.")
            try:
                url = entry["download_url"] + f"?download=1&attempt={time.time_ns()}"
                headers = {"User-Agent": "SkyTwin-dataset-setup/1.0"}
                if offset:
                    headers["Range"] = f"bytes={offset}-"
                with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as response:
                    if offset and (response.status != 206 or not response.headers.get("Content-Range", "").startswith(f"bytes {offset}-")):
                        raise RuntimeError("Server did not honor resume; partial file preserved.")
                    mode = "ab" if offset else "wb"
                    last_print = 0.0
                    with partial.open(mode) as output:
                        while block := response.read(4 * 1024 * 1024):
                            if offset + len(block) > SIZE:
                                raise RuntimeError("Server returned more bytes than expected")
                            output.write(block)
                            offset += len(block)
                            now = time.monotonic()
                            if now - last_print > 15:
                                print(f"DOWNLOAD {offset}/{SIZE} ({offset / SIZE:.1%})", flush=True)
                                last_print = now
                if offset != SIZE:
                    raise RuntimeError(f"Incomplete response: {offset}/{SIZE}")
                break
            except (OSError, RuntimeError) as error:
                print(f"Attempt {attempt}: {error}", flush=True)
                if attempt == 8:
                    raise
                time.sleep(min(attempt * 2, 10))
        if partial.stat().st_size != SIZE or hashes(partial)[0] != MD5:
            raise RuntimeError("Dataset checksum mismatch; partial file preserved, DO NOT extract.")
        partial.rename(target)
    actual_md5, sha256 = hashes(target)
    if target.stat().st_size != SIZE or actual_md5 != MD5:
        raise RuntimeError("Existing archive failed integrity verification")
    proof = {"article": 24123666, "version": 2, "file_id": FILE_ID, "size": SIZE, "md5": actual_md5, "sha256": sha256, "license": "CC BY 4.0", "attribution": "Ze Yang, River Floating Debris Dataset, Figshare v2, DOI: 10.6084/m9.figshare.24123666.v2"}
    (folder / "download-verification.json").write_text(json.dumps(proof, indent=2), encoding="utf-8")
    print("DOWNLOAD_VERIFIED " + json.dumps(proof), flush=True)


if __name__ == "__main__":
    main()
