"""Explicit unchanged-migration or exact approved-artifact postdeployment check.
Never used as a regular candidate-content PR gate.
"""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request
from urllib.parse import quote
from check_staged import inventory


def require_unchanged(root, baseline, manifest):
    old_manifest = baseline / "publish-manifest.json"
    if old_manifest.is_file():
        old = json.loads(old_manifest.read_text(encoding="utf-8"))
        if set(old) != set(manifest): raise ValueError("Migration changes the approved public inventory")
    else:
        print("NOTE: pre-manifest baseline; checking only explicitly approved public paths, not omitted baseline inventory")
    for name in manifest:
        if (root / name).read_bytes() != (baseline / name).read_bytes():
            raise ValueError("Migration changes public bytes: " + name)


def verify_published(approved, base_url):
    for name, expected in approved.items():
        request = urllib.request.Request(base_url.rstrip("/") + "/" + quote(name, safe="/"), headers={"User-Agent": "Governance-availability-check/2.0", "Cache-Control": "no-cache"})
        with urllib.request.urlopen(request, timeout=15) as response:
            if response.status != 200: raise ValueError(f"HTTP {response.status}: {name}")
            if hashlib.sha256(response.read()).hexdigest() != expected:
                raise ValueError("Published bytes differ from exact approved artifact: " + name)
        print("PASS", name)
    print(f"Verified {len(approved)}/{len(approved)} approved public paths")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["migration", "postdeploy"], required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--root", type=Path, default=Path("_site"))
    parser.add_argument("--manifest", type=Path, default=Path("publish-manifest.json"))
    parser.add_argument("--approved-inventory", type=Path, required=True)
    parser.add_argument("--unchanged-from", type=Path)
    args = parser.parse_args()
    approved = json.loads(args.approved_inventory.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if set(approved) != set(manifest) or inventory(args.root) != approved:
        raise ValueError("Local artifact no longer equals the pre-upload approved inventory")
    if args.mode == "migration":
        if not args.unchanged_from: parser.error("migration requires --unchanged-from")
        require_unchanged(args.root, args.unchanged_from, manifest)
    elif args.unchanged_from: parser.error("--unchanged-from is only valid for migration")
    verify_published(approved, args.base_url)

if __name__ == "__main__": main()
