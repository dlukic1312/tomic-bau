"""Check public baseline and candidate byte compatibility without deployment."""
import hashlib
import json
import urllib.request
from pathlib import Path
from urllib.parse import quote

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / "publish-manifest.json").read_text())
base = "https://dlukic1312.github.io/tomic-bau/"
failures = []
for name in manifest:
    url = base + quote(name, safe="/")
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent":"Governance-availability-check/1.0"}), timeout=15) as response:
            data = response.read()
            if response.status != 200:
                raise ValueError(f"HTTP {response.status}")
            expected = (root / "_site" / name).read_bytes()
            if hashlib.sha256(data).digest() != hashlib.sha256(expected).digest():
                raise ValueError("live bytes differ from candidate")
        print("PASS", name)
    except Exception as exc:
        failures.append(name)
        print("UNVERIFIED", name, str(exc))
print(f"Verified {len(manifest)-len(failures)}/{len(manifest)} public paths")
if failures:
    raise SystemExit(1)
