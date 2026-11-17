"""Download the author's public HAIDA archive; never execute archive contents."""
from __future__ import annotations
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
from pathlib import PurePosixPath
import subprocess
import time
import urllib.parse
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILE_ID = "12ieYe9479Yee9eYADrGal6CYKxg2lwG_"
SIZE = 979276090
SHA256 = "64ed1b86fe0b5833e1c7b2385e623fc8eb4fb24f7fb6f9aea05acf46243fda6b"
SOURCE = "https://github.com/LiaoSteve/HAIDA-Trash-Dataset-High-Resolution-Aerial-image/tree/HAIDA-trash-dataset"


class DownloadForm(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.action = None
        self.fields = {}
        self.inside = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form" and attrs.get("id") == "download-form":
            self.inside = True
            self.action = attrs.get("action")
        if self.inside and tag == "input" and attrs.get("type") == "hidden":
            self.fields[attrs["name"]] = attrs.get("value", "")

    def handle_endtag(self, tag):
        if tag == "form":
            self.inside = False


def main() -> None:
    folder = ROOT / "data/raw/haida"
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / "HAIDA.zip"
    partial = target.with_suffix(".zip.part")
    if not target.exists() and (not partial.exists() or partial.stat().st_size != SIZE):
        start = f"https://drive.usercontent.google.com/uc?id={FILE_ID}&export=download"
        with urllib.request.urlopen(start, timeout=60) as response:
            if "text/html" not in response.headers.get("Content-Type", ""):
                raise RuntimeError("Unexpected response; inspect download before proceeding")
            text = response.read(100_000).decode("utf-8")
        form = DownloadForm()
        form.feed(text)
        if form.action != "https://drive.usercontent.google.com/download" or form.fields.get("id") != FILE_ID:
            raise RuntimeError("Unexpected download form; no sign-in/CAPTCHA or warning bypass attempted")
        url = form.action + "?" + urllib.parse.urlencode(form.fields)
        offset = partial.stat().st_size if partial.exists() else 0
        headers = {"Range": f"bytes={offset}-"} if offset else {}
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as response:
            if "text/html" in response.headers.get("Content-Type", ""):
                raise RuntimeError("No archive returned; may require author access")
            if offset and (response.status != 206 or not response.headers.get("Content-Range", "").startswith(f"bytes {offset}-")):
                raise RuntimeError("Resume not honored; existing partial preserved")
            length = response.headers.get("Content-Length")
            expected = offset + int(length) if length else None
            print(f"HAIDA_DOWNLOAD_START offset={offset} expected={expected}", flush=True)
            last_print = 0.0
            with partial.open("ab" if offset else "wb") as output:
                while chunk := response.read(4 * 1024 * 1024):
                    output.write(chunk)
                    offset += len(chunk)
                    if time.monotonic() - last_print > 15:
                        print(f"HAIDA_DOWNLOAD {offset}/{expected}", flush=True)
                        last_print = time.monotonic()
            if expected and offset != expected:
                raise RuntimeError("Incomplete archive; partial preserved for resume")
    candidate = target if target.exists() else partial
    if candidate.stat().st_size != SIZE:
        raise RuntimeError("HAIDA source changed or download incomplete; inspect before use")
    with zipfile.ZipFile(candidate) as archive:
        for info in archive.infolist():
            path = PurePosixPath(info.filename)
            if path.is_absolute() or ".." in path.parts or any(char in info.orig_filename for char in ("\\", ":", "\x00")):
                raise RuntimeError(f"Unsafe archive entry: {info.filename}")
            if not info.is_dir() and path.suffix.lower() not in (".jpg", ".xml"):
                raise RuntimeError(f"Unexpected non-data entry: {info.filename}")
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise RuntimeError("Symlinks are not allowed in this dataset")
    # HAIDA uses PPMd ZIP compression (method 98), unsupported by Python zipfile.
    # Windows' built-in libarchive tar supports it. Reading every member checks
    # decompression/integrity without executing any downloaded file.
    tar = Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32/tar.exe"
    subprocess.run([str(tar), "-xOf", str(candidate)], stdout=subprocess.DEVNULL, check=True)
    if not target.exists():
        partial.rename(target)
    sha = hashlib.sha256()
    with target.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            sha.update(block)
    if sha.hexdigest() != SHA256:
        raise RuntimeError("Archive differs from the inspected HAIDA version; preserved, do not prepare/train")
    proof = {"source": SOURCE, "file_id": FILE_ID, "bytes": target.stat().st_size, "sha256": sha.hexdigest(),
             "integrity": "TLS source + full libarchive decompression check + locally recorded SHA-256; publisher does not provide a checksum",
             "scope": "UAV coastal/harbor surface litter, NOT Hangzhou river validation",
             "attribution": "Y. H. Liao and J. G. Juang (2021), Application of Unmanned Aerial Vehicles for Marine Trash Detection and Real-Time Monitoring System, NTOU"}
    (folder / "download-verification.json").write_text(json.dumps(proof, indent=2), encoding="utf-8")
    print("HAIDA_DOWNLOAD_VERIFIED " + json.dumps(proof), flush=True)


if __name__ == "__main__":
    main()
