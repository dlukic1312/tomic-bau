"""Synthetic contract tests: no production systems or real secrets."""
import contextlib
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_staged import validate, inventory
from check_live_baseline import require_unchanged, verify_published
import stage_pages

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args): pass

class PublicationContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.site = self.root / "candidate"; self.site.mkdir()
        self.base = self.root / "baseline"; self.base.mkdir()
        self.manifest = ["index.html", "style.css", "logo.svg", "detail.html"]
        files = {"index.html": '<html><head><link href="style.css" rel="stylesheet"></head><body><a href="detail.html#details">Details</a><img src="logo.svg" alt="Logo"></body></html>',
                 "detail.html": '<html><body><h1 id="details">Details</h1></body></html>',
                 "style.css": 'body { background-image: url("logo.svg"); }',
                 "logo.svg": '<svg xmlns="http://www.w3.org/2000/svg"/>'}
        for directory in [self.site, self.base]:
            for name, content in files.items(): (directory/name).write_text(content, encoding="utf-8")
        (self.base/"publish-manifest.json").write_text(json.dumps(self.manifest))
    def tearDown(self): self.temp.cleanup()
    def test_unchanged_migration_passes(self):
        validate(self.site, self.manifest)
        require_unchanged(self.site, self.base, self.manifest)
    def test_intended_content_edit_accepted_as_candidate(self):
        (self.site/"detail.html").write_text('<html><body><h1 id="details">Intended new copy</h1></body></html>')
        validate(self.site, self.manifest)  # no comparison to current live bytes
        with self.assertRaisesRegex(ValueError, "changes public bytes"):
            require_unchanged(self.site, self.base, self.manifest)
    def test_missing_resource_fails(self):
        (self.site/"logo.svg").unlink()
        with self.assertRaisesRegex(ValueError, "missing/out-of-scope"):
            validate(self.site, self.manifest)
    def test_wrong_navigation_fails(self):
        path=self.site/"index.html"; path.write_text(path.read_text().replace("#details", "#wrong"))
        with self.assertRaisesRegex(ValueError, "missing navigation target"):
            validate(self.site, self.manifest)
    def test_css_resource_fails(self):
        (self.site/"style.css").write_text('body{background:url(missing.png)}')
        with self.assertRaisesRegex(ValueError, "missing/out-of-scope"):
            validate(self.site, self.manifest)
    def test_outside_link_fails(self):
        (self.site/"index.html").write_text('<a href="../outside.html">No escape</a>')
        with self.assertRaisesRegex(ValueError, "missing/out-of-scope"):
            validate(self.site, self.manifest)
    def test_artifact_symlink_rejected_before_inventory_read(self):
        outside=self.root/"outside.txt"; outside.write_text("synthetic canary")
        try: (self.site/"linked.txt").symlink_to(outside)
        except OSError as exc: self.skipTest("Symlink creation unavailable: " + str(exc))
        with self.assertRaisesRegex(ValueError,"must not contain symlinks"):
            inventory(self.site)
    def test_unlisted_root_public_file_warns(self):
        source=self.root/"source";source.mkdir()
        (source/"index.html").write_text('<h1>OK</h1>')
        (source/"new-page.html").write_text('<h1>Needs review</h1>')
        (source/"publish-manifest.json").write_text('["index.html"]')
        old_root,old_out=stage_pages.ROOT,stage_pages.OUT
        try:
            stage_pages.ROOT,stage_pages.OUT=source,source/"_site"
            output=io.StringIO()
            with contextlib.redirect_stdout(output): stage_pages.stage()
            self.assertIn("WARNING: unlisted potential public file",output.getvalue())
            self.assertIn("new-page.html",output.getvalue())
            self.assertFalse((source/"_site/new-page.html").exists())
        finally: stage_pages.ROOT,stage_pages.OUT=old_root,old_out
    def test_exact_approved_published_bytes_and_mismatch(self):
        approved=inventory(self.site)
        server=ThreadingHTTPServer(("127.0.0.1",0),functools.partial(QuietHandler,directory=str(self.site)))
        worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        try:
            url=f"http://127.0.0.1:{server.server_port}/"
            verify_published(approved,url)
            (self.site/"index.html").write_text("Published unexpected bytes")
            with self.assertRaisesRegex(ValueError,"exact approved artifact"):
                verify_published(approved,url)
        finally: server.shutdown();server.server_close();worker.join()
    def test_regular_pr_has_no_live_gate_and_deploy_is_staged(self):
        root=Path(__file__).resolve().parents[1]
        pr=(root/".github/workflows/verify-pages.yml").read_text()
        self.assertNotIn("check_live_baseline.py",pr)
        self.assertIn("scripts/check_staged.py",pr)
        path=root/".github/workflows/deploy-pages.yml"
        if not path.exists(): path=root/".github/workflows/pages.yml"
        deploy=path.read_text()
        self.assertLess(deploy.index("scripts/check_staged.py"),deploy.index("actions/upload-pages-artifact"))
        self.assertIn("--mode postdeploy",deploy)
        self.assertNotIn("continue-on-error",deploy[deploy.index("Fail-closed browser"):])
        if "baseline-source" in pr:
            self.assertIn("github.event.pull_request.base.sha",pr)
            self.assertNotIn("fd4a874",pr)

if __name__ == "__main__": unittest.main()
