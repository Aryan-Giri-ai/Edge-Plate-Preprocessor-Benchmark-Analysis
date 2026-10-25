#!/usr/bin/env python3
"""Open a generated HTML report with the system browser."""
import argparse
import os
from pathlib import Path
import webbrowser
p=argparse.ArgumentParser(description=__doc__)
p.add_argument("html",type=Path)
a=p.parse_args()
path=a.html.resolve()
if not path.is_file():
    p.error(f"missing report: {path}")
print(f"Report: {path}")
try:
    if os.name=="nt":
        os.startfile(str(path))
    elif not webbrowser.open(path.as_uri()):
        print("Open the printed HTML path manually in your browser.")
except OSError as error:
    print(f"Browser launch unavailable: {error}. Open the HTML path manually.")

