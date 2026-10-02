"""Organise the attachments in folders by year and rewrite the announcements.

Replaces rewrite.py + addyear.py. Works in the project folder (old layout):

    announcements.csv, failed.txt, downloads/, downloads_case/   (inputs)

    python byyear.py                      build everything
    python byyear.py --verify http://IP:8080    check the files on the new server

Each file goes to the folder of the year of the (earliest) announcement that
links to it:  downloads_byyear/2025/pdf/file.pdf
On the server:  /wp-content/uploads/vo-archive/2025/pdf/file.pdf

Outputs:
    announcements_new.csv     import this in WordPress (has a 'year' column)
    downloads_byyear/         upload this to the server
    downloads_byyear_extra/   only if two names differ just in letter case within
                              the same year (Windows cannot hold both); upload
                              it to the same place as downloads_byyear
    redirects_nginx.conf      old URL -> new URL, for Plesk (nginx directives)
    redirects_apache.htaccess same for Apache
    files_byyear.csv          list of new files with size and hash (for --verify)
"""
import argparse
import csv
import hashlib
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import quote, unquote

import requests
from bs4 import BeautifulSoup

# ---- settings -------------------------------------------------------------
SITE = "https://vo.duth.gr"                       # old site, no trailing slash
OLD_MEDIA = "/images/"                            # old media folder
NEW_BASE = "/wp-content/uploads/vo-archive/"      # new base folder (year folders go below)
OLD_POST_PATH = "/index.php/el/anakoinoseis/"     # old URL of the announcements
NEW_POST_PATH = "/anakoinoseis/"                  # new URL of the announcements
BROKEN_NOTE = "(το αρχείο δεν είναι πλέον διαθέσιμο)"

SRC_DIRS = [Path("downloads_case/1"), Path("downloads_case/2"), Path("downloads")]
OUT_DIR = Path("downloads_byyear")
OUT_EXTRA = Path("downloads_byyear_extra")
# ---------------------------------------------------------------------------


def old_media_path(href):
    """'/images/...' (decoded) if the link points to the old media folder, else None."""
    h = href.strip()
    if h.startswith(SITE):
        h = h[len(SITE):]
    if h.startswith(OLD_MEDIA.lstrip("/")):
        h = "/" + h
    if h.startswith(OLD_MEDIA):
        return unquote(h.split("#")[0].split("?")[0])
    return None


def fix_special(html):
    for scheme in ("tel:", "mailto:"):
        html = html.replace(f"{SITE}/{scheme}", scheme)
    return html


def media_elements(soup):
    for tag, attr in (("a", "href"), ("img", "src")):
        for el in soup.find_all(tag, attrs={attr: True}):
            path = old_media_path(el[attr])
            if path:
                yield el, attr, path


def new_url(path, year):
    return NEW_BASE + year + "/" + quote(path[len(OLD_MEDIA):], safe="/")


def build_index():
    """Exact-case path -> file on disk (case dirs first, so both variants are found)."""
    index = {}
    for root in SRC_DIRS:
        if root.exists():
            for p in root.rglob("*"):
                if p.is_file():
                    index.setdefault("/" + p.relative_to(root).as_posix(), p)
    return index


def build():
    with open("announcements.csv", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    failed = set()
    if Path("failed.txt").exists():
        for line in Path("failed.txt").read_text(encoding="utf-8").splitlines():
            if line.strip():
                failed.add(unquote(line.split("\t")[0].strip()))

    index = build_index()

    # pass 1: which years link to each file
    file_years = {}
    for r in rows:
        year = (r["date"] or "")[:4] or "undated"
        soup = BeautifulSoup(fix_special(r["content"]), "html.parser")
        for _, _, path in media_elements(soup):
            if SITE + path not in failed:
                file_years.setdefault(path, set()).add(year)
    file_year = {p: min(ys) for p, ys in file_years.items()}

    # pass 2: rewrite the announcements
    removed, other_links, with_img = 0, set(), 0
    for r in rows:
        year = (r["date"] or "")[:4] or "undated"
        html = fix_special(r["content"])
        soup = BeautifulSoup(html, "html.parser")
        if soup.find("img"):
            with_img += 1
        for el, attr, path in list(media_elements(soup)):
            if SITE + path in failed and el.name == "a":
                el.insert_after(" " + BROKEN_NOTE)
                el.unwrap()
                removed += 1
                continue
            el[attr] = new_url(path, file_year.get(path, year))
        for a in soup.find_all("a", href=True):
            if a["href"].startswith(SITE + "/"):
                other_links.add(a["href"])
        r["content"] = str(soup)
        r["year"] = year

    with open("announcements_new.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # copy the files into year folders
    for d in (OUT_DIR, OUT_EXTRA):
        if d.exists():
            shutil.rmtree(d)
    planned, missing, manifest, extra = {}, [], [], 0
    per_year = {}
    redirects = []
    for path, year in sorted(file_year.items()):
        src = index.get(path)
        if src is None:
            missing.append(path)
            continue
        rel = f"{year}/{path[len(OLD_MEDIA):]}"
        root = OUT_DIR
        if rel.lower() in planned and planned[rel.lower()] != rel:
            root, extra = OUT_EXTRA, extra + 1   # same name except letter case
        else:
            planned[rel.lower()] = rel
        dest = root / Path(*rel.split("/"))
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        data = dest.read_bytes()
        target = new_url(path, year)
        manifest.append((target, len(data), hashlib.sha256(data).hexdigest()[:12]))
        redirects.append((path, target))
        per_year[year] = per_year.get(year, 0) + 1

    with open("files_byyear.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["path", "size", "sha256_12"])
        w.writerows(manifest)

    write_redirects(redirects)

    multi = sum(1 for ys in file_years.values() if len(ys) > 1)
    print("announcements:", len(rows))
    print("with <img> inside:", with_img)
    print("broken links removed:", removed)
    print("files placed in year folders:", len(manifest))
    for y in sorted(per_year):
        print("  ", y, per_year[y])
    print("files linked from more than one year (placed in the earliest):", multi)
    print("names that differ only in case within a year (-> downloads_byyear_extra):", extra)
    print("files with no source on disk:", len(missing))
    for p in missing[:20]:
        print("   MISSING", p)
    print(f"links to {SITE} outside {OLD_MEDIA}:", len(other_links))
    for u in sorted(other_links)[:20]:
        print("  ", u)


def write_redirects(redirects):
    skipped = []
    nginx = ["# Plesk: Apache & nginx Settings -> Additional nginx directives"]
    apache = ["# .htaccess, above the '# BEGIN WordPress' block", "RewriteEngine On"]
    for old, new in redirects:
        if any(c in old for c in '"$\\'):
            skipped.append(old)
            continue
        nginx.append(f'location = "{old}" {{ return 301 "{new}"; }}')
        apache.append(f'RewriteRule "^{re.escape(old.lstrip("/"))}$" "{new}" [R=301,L,NE]')
    nginx.append(r"rewrite ^%s(.+)$ %s$1/ permanent;" % (re.escape(OLD_POST_PATH), NEW_POST_PATH))
    apache.append('RewriteRule "^%s(.+)$" "%s$1/" [R=301,L]' % (re.escape(OLD_POST_PATH.lstrip("/")), NEW_POST_PATH))
    Path("redirects_nginx.conf").write_text("\n".join(nginx) + "\n", encoding="utf-8")
    Path("redirects_apache.htaccess").write_text("\n".join(apache) + "\n", encoding="utf-8")
    if skipped:
        print("redirects skipped (special characters in the name):", len(skipped))


def verify(base):
    base = base.rstrip("/")
    with open("files_byyear.csv", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    bad = 0
    for r in rows:
        resp = requests.get(base + r["path"], timeout=60, stream=True,
                            headers={"User-Agent": "Mozilla/5.0"})
        resp.close()
        length = resp.headers.get("Content-Length")
        problem = None
        if resp.status_code != 200:
            problem = f"HTTP {resp.status_code}"
        elif length and int(length) != int(r["size"]):
            problem = f"size {length} != {r['size']}"
        if problem:
            bad += 1
            print("PROBLEM", problem, r["path"])
    print(f"checked {len(rows)} files, problems: {bad}")
    print("RESULT:", "all OK" if bad == 0 else f"{bad} problem(s)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", metavar="BASE_URL", help="e.g. http://83.212.145.131:8080")
    args = ap.parse_args()
    if args.verify:
        verify(args.verify)
    else:
        build()
