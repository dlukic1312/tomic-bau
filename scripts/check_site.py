#!/usr/bin/env python3
"""Static checks for the TOMIC BAU GitHub Pages website.

Run after the approved header image is generated in the deployment workflow.
No network access or third-party dependencies required.
"""
from html.parser import HTMLParser
from pathlib import Path
import sys
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
PAGES = ["index.html", "asphaltbau.html", "kabelbau.html", "impressum.html", "datenschutz.html"]
ORIGIN = "https://tomic-bau.de"
CANONICALS = {
    "index.html": ORIGIN + "/",
    "asphaltbau.html": ORIGIN + "/asphaltbau.html",
    "kabelbau.html": ORIGIN + "/kabelbau.html",
}
errors = []

class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids, self.links, self.images, self.scripts, self.forms = [], [], [], [], []
        self.is_script = False
        self.in_head = False
        self.has_description = False
        self.has_title = False
        self.has_lang = False
        self.canonicals, self.robots = [], []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.has_lang = a.get("lang") == "de"
        if tag == "head":
            self.in_head = True
        if self.in_head and tag == "title":
            self.has_title = True
        if self.in_head and tag == "meta" and a.get("name") == "description":
            self.has_description = bool(a.get("content"))
        if self.in_head and tag == "link" and a.get("rel") == "canonical":
            self.canonicals.append(a.get("href"))
        if self.in_head and tag == "meta" and a.get("name", "").lower() in {"robots", "googlebot"}:
            self.robots.extend(a.get("content", "").lower().replace(",", " ").split())
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "a":
            self.links.append((a.get("href", ""), a))
        if tag == "img":
            self.images.append(a)
        if tag == "script" and not a.get("src"):
            self.is_script = True
        if tag == "form":
            self.forms.append(a)
    def handle_endtag(self, tag):
        if tag == "script":
            self.is_script = False
        if tag == "head":
            self.in_head = False
    def handle_data(self, data):
        if self.is_script:
            self.scripts.append(data)

for filename in PAGES:
    path = ROOT / filename
    if not path.is_file():
        errors.append(f"Missing page: {filename}")
        continue
    src = path.read_text(encoding="utf-8")
    parser = PageParser()
    parser.feed(src)
    if not parser.has_lang:
        errors.append(f"{filename}: missing html lang=de")
    if not parser.has_title:
        errors.append(f"{filename}: missing title")
    if not parser.has_description:
        print(f"NOTE: {filename}: no meta description")
    if len(parser.ids) != len(set(parser.ids)):
        errors.append(f"{filename}: duplicate HTML IDs")
    for img in parser.images:
        link = img.get("src", "").split("?")[0]
        if not img.get("alt") and img.get("alt") != "":
            errors.append(f"{filename}: image without alt ({link})")
        if link and not (link.startswith("http") or link.startswith("data:")):
            if not (ROOT / link).is_file():
                errors.append(f"{filename}: missing image {link}")
    for href, attrs in parser.links:
        if not href or href.startswith(("mailto:", "tel:", "https://", "http://")):
            continue
        if href.startswith("#"):
            target = href[1:]
            if target and target not in parser.ids:
                errors.append(f"{filename}: broken anchor {href}")
        else:
            target = href.split("#")[0].split("?")[0]
            if target and not (ROOT / target).is_file():
                errors.append(f"{filename}: missing link {href}")
        if attrs.get("target") == "_blank" and "noopener" not in attrs.get("rel", ""):
            errors.append(f"{filename}: target=_blank without noopener ({href})")
    if filename in CANONICALS:
        if parser.canonicals != [CANONICALS[filename]]:
            errors.append(f"{filename}: missing or incorrect canonical URL")
        if {"noindex", "none", "nofollow"}.intersection(parser.robots):
            errors.append(f"{filename}: public page restricts search indexing or crawling")
        if not parser.has_description:
            errors.append(f"{filename}: missing search description")
    if filename == "index.html":
        for text in ("Asphalt- und Kabelbau<br/>aus Kirchzarten", "Kabelbau &amp; Glasfaser", "Langjährige Erfahrung", "Pflaster-, Wege- &amp; Stützwandbau", "impressum.html", "datenschutz.html", "tel:+4915730993989"):
            if text not in src:
                errors.append(f"index.html: required content missing: {text}")
    print(f"Checked {filename}: {len(parser.links)} links, {len(parser.images)} images, {len(parser.ids)} IDs")

try:
    sitemap = ElementTree.parse(ROOT / "sitemap.xml")
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locations = [node.text for node in sitemap.findall("sm:url/sm:loc", namespace)]
    if sorted(locations) != sorted(CANONICALS.values()):
        errors.append("Sitemap must list each indexable canonical URL once")
    robots = (ROOT / "robots.txt").read_text(encoding="utf-8")
    if robots.splitlines() != ["User-agent: *", "Allow: /", f"Sitemap: {ORIGIN}/sitemap.xml"]:
        errors.append("robots.txt must allow crawling and advertise the production sitemap")
except (OSError, ElementTree.ParseError) as exc:
    errors.append(f"Cannot read SEO files: {exc}")

if errors:
    print("\nFAIL:\n" + "\n".join(" - " + e for e in errors))
    sys.exit(1)
print("PASS: static website checks")
