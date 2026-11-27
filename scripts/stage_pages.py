"""Stage only explicitly approved files for Pages; fail closed."""
import hashlib
import json
import shutil
import tempfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "_site"

def stage():
    entries = json.loads((ROOT / "publish-manifest.json").read_text(encoding="utf-8"))
    if not isinstance(entries, list) or not entries or len(entries) != len(set(entries)):
        raise ValueError("Invalid or duplicate manifest entries")
    if "index.html" not in entries:
        raise ValueError("Missing index.html")
    if OUT.exists() or OUT.is_symlink():
        raise ValueError("Output must not already exist")
    for entry in entries:
        p = PurePosixPath(entry)
        if p.is_absolute() or p.as_posix() != entry or any(part in ("..", ".") or part.startswith(".") for part in p.parts):
            raise ValueError("Unsafe path: " + entry)
        if p.suffix.lower() not in {".html",".css",".js",".json",".png",".jpg",".jpeg",".webp",".svg",".ico",".txt",".xml",".woff",".woff2"} and entry != "CNAME":
            raise ValueError("Unsupported public type: " + entry)
        if p.parts[0] in {"docs","scripts","tests","knowledge"}:
            raise ValueError("Internal path: " + entry)
        src = ROOT / entry
        if not src.is_file() or any((ROOT / Path(*p.parts[:i])).is_symlink() for i in range(1,len(p.parts)+1)):
            raise ValueError("Missing or linked file: " + entry)
    public_types = {".html", ".css", ".js", ".json", ".png", ".jpg", ".jpeg", ".webp", ".svg", ".ico", ".txt", ".xml", ".woff", ".woff2"}
    for source in sorted(ROOT.iterdir()):
        if source.is_file() and (source.suffix.lower() in public_types or source.name == "CNAME") and source.name not in entries:
            print("WARNING: unlisted potential public file (review manifest intentionally): " + source.name)
    with tempfile.TemporaryDirectory(dir=ROOT) as temp:
        dest = Path(temp) / "site"
        dest.mkdir()
        for entry in entries:
            target = dest / entry
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / entry, target)
            if hashlib.sha256(target.read_bytes()).digest() != hashlib.sha256((ROOT / entry).read_bytes()).digest():
                raise ValueError("Copy mismatch: " + entry)
        actual = {p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file()}
        if actual != set(entries):
            raise ValueError("Publication inventory mismatch")
        dest.rename(OUT)
    print(f"Staged {len(entries)} explicitly listed files")

if __name__ == "__main__":
    stage()
