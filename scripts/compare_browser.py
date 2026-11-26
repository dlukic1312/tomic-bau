import pathlib
import subprocess
import sys
import re
import os

def run(root):
    p = subprocess.run(["node", str(pathlib.Path("scripts/check_browser.cjs").resolve())], env=dict(os.environ, GOVERNANCE_BROWSER_ROOT=root), capture_output=True, text=True)
    print(p.stdout, p.stderr)
    lines = [line.strip() for line in p.stderr.splitlines() if re.match(r"^(\d+px (horizontal overflow|broken images|JS):|\d+px menu |Filter shows|Reference image modal)",line)]
    if p.returncode and not lines:
        raise RuntimeError("Browser infrastructure or unexpected test failure")
    return set(lines)

baseline=run("http://127.0.0.1:8766/")
candidate=run("http://127.0.0.1:8765/")
print("Baseline findings:", sorted(baseline))
print("Candidate findings:", sorted(candidate))
if candidate-baseline:
    print("New regressions:",sorted(candidate-baseline))
    sys.exit(1)
print("No new findings relative to baseline; existing issues remain open.")
