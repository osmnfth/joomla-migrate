"""Write redirects_by_year.txt: every old URL and its new URL, grouped by year.

    python redirectlist.py                          -> redirects_byyear/redirects_<year>.txt
                                                       (one file per year) + redirects_by_year.txt (all)
    python redirectlist.py --test http://IP:8080    -> request old URLs, check they redirect
    python redirectlist.py --test http://IP:8080 --sample 100   (only ~100 URLs)

Needs announcements_new.csv and redirects_nginx.conf (both made by byyear.py).
Format of the txt: old URL <TAB> new URL. Lines starting with '#' are comments.
"""
import argparse
import csv
import re
import time
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

import requests

from byyear import SITE, OLD_POST_PATH, NEW_POST_PATH, NEW_BASE


def load():
    posts, files = defaultdict(list), defaultdict(list)
    with open("announcements_new.csv", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            posts[r["year"]].append((OLD_POST_PATH + quote(r["old_slug"]),
                                     NEW_POST_PATH + r["slug"] + "/"))
    rule = re.compile(r'^location = "(.+)" \{ return 301 "(.+)"; \}$')
    for line in Path("redirects_nginx.conf").read_text(encoding="utf-8").splitlines():
        m = rule.match(line)
        if m:
            old, new = m.groups()
            y = re.match(re.escape(NEW_BASE) + r"([^/]+)/", new)
            files[y.group(1) if y else "undated"].append((quote(old), new))
    return posts, files


def year_block(y, posts, files):
    p, f = sorted(posts.get(y, [])), sorted(files.get(y, []))
    out = [f"# ===== {y}  ({len(p)} announcements, {len(f)} files) =====",
           f"# Announcements {y}"]
    out += [f"{SITE}{o}\t{SITE}{n}" for o, n in p]
    out += [f"# Files {y}"]
    out += [f"{SITE}{o}\t{SITE}{n}" for o, n in f]
    out.append("")
    return out


def write_txt():
    posts, files = load()
    years = sorted(set(posts) | set(files))
    header = [
        "# 301 redirects.  Format: old URL<TAB>new URL",
        f"# Site: {SITE}",
        "# WordPress may change a slug (e.g. adds -2 to duplicates): check after the import.",
        "",
    ]
    folder = Path("redirects_byyear")
    folder.mkdir(exist_ok=True)
    combined = list(header)
    for y in years:
        block = year_block(y, posts, files)
        combined += block
        (folder / f"redirects_{y}.txt").write_text("\n".join(header + block), encoding="utf-8")
    Path("redirects_by_year.txt").write_text("\n".join(combined), encoding="utf-8")
    print("written: redirects_byyear/redirects_<year>.txt (one per year) and redirects_by_year.txt (all)")
    for y in years:
        print(f"  {y}: {len(posts.get(y, []))} announcements, {len(files.get(y, []))} files")
    print("  total:", sum(len(v) for v in posts.values()) + sum(len(v) for v in files.values()))


def test(base, sample):
    base = base.rstrip("/")
    posts, files = load()
    items = [x for d in (posts, files) for y in sorted(d) for x in d[y]]
    if sample and len(items) > sample:
        items = items[::max(1, len(items) // sample)]
    bad = 0
    for old, new in items:
        r = requests.get(base + old, allow_redirects=False, timeout=30,
                         headers={"User-Agent": "Mozilla/5.0"})
        got = unquote(urlparse(r.headers.get("Location", "")).path)
        if r.status_code != 301 or got != unquote(new):
            bad += 1
            print(f"PROBLEM {r.status_code}  {old}  ->  {got or '(no Location)'}  (expected {new})")
        time.sleep(0.03)
    print(f"checked {len(items)} URLs, problems: {bad}")
    print("RESULT:", "all OK" if bad == 0 else f"{bad} problem(s)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", metavar="BASE_URL")
    ap.add_argument("--sample", type=int, default=0)
    a = ap.parse_args()
    test(a.test, a.sample) if a.test else write_txt()
