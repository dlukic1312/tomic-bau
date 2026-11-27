"""Validate the exact public artifact (local files, resources and navigation)."""
import argparse
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

class Document(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.ids, self.refs = set(), []
        self.feed(text)
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"): self.ids.add(attrs["id"])
        if tag == "a" and attrs.get("name"): self.ids.add(attrs["name"])
        for key in ("src", "poster", "href"):
            if attrs.get(key) and (key != "href" or tag in {"a", "link", "use"}):
                self.refs.append((attrs[key], tag == "a"))
        if attrs.get("srcset"):
            self.refs.extend((entry.strip().split()[0], False) for entry in attrs["srcset"].split(",") if entry.strip())


def inventory(root):
    if any(p.is_symlink() for p in root.rglob("*")):
        raise ValueError("Artifact must not contain symlinks")
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}


def validate(root, manifest):
    root = root.resolve()
    actual = inventory(root)
    errors = []
    if set(actual) != set(manifest): errors.append("Artifact inventory differs from approved manifest")
    docs = {name: Document((root / name).read_text(encoding="utf-8")) for name in actual if name.endswith(".html")}
    for name in actual:
        refs = docs[name].refs if name in docs else []
        if name.endswith(".css"):
            refs = [(a or b or c, False) for a,b,c in re.findall(r"url\(\s*(?:'([^']*)'|\"([^\"]*)\"|([^)]*))\s*\)", (root/name).read_text(encoding="utf-8"))]
        for ref, navigation in refs:
            url = urlsplit(ref.strip())
            if url.scheme or url.netloc or not (url.path or url.fragment): continue
            target = (root / unquote(url.path).lstrip("/")) if url.path.startswith("/") else (root / name).parent / unquote(url.path)
            if not url.path: target = root / name
            if target.is_dir(): target /= "index.html"
            target = target.resolve()
            if not target.is_relative_to(root) or not target.is_file():
                errors.append(f"{name}: missing/out-of-scope local resource or link {ref}"); continue
            dest = target.relative_to(root).as_posix()
            if navigation and url.fragment and dest in docs and unquote(url.fragment) not in docs[dest].ids:
                errors.append(f"{name}: missing navigation target {ref}")
    if errors: raise ValueError("\n".join(errors))
    return actual


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("_site"))
    parser.add_argument("--manifest", type=Path, default=Path("publish-manifest.json"))
    parser.add_argument("--write-inventory", type=Path)
    args = parser.parse_args()
    result = validate(args.root, json.loads(args.manifest.read_text(encoding="utf-8")))
    if args.write_inventory: args.write_inventory.write_text(json.dumps(result, sort_keys=True, indent=2)+"\n", encoding="utf-8")
    print(f"PASS: staged links/resources/navigation and exact inventory ({len(result)} files)")

if __name__ == "__main__": main()
