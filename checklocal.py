"""Local check of everything produced by byyear.py, BEFORE uploading anything.

    python checklocal.py

Checks announcements_new.csv, the year folders, the manifest and the redirect
files, and prints OK / WARN / ERROR lines. Exit code 1 if there are errors.
Uses the same settings as byyear.py (edit them there).
"""
import csv
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import unquote

from bs4 import BeautifulSoup

from byyear import SITE, OLD_MEDIA, NEW_BASE, OUT_DIR, OUT_EXTRA

SAFE_EXT = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt", ".ods", ".rtf",
            ".txt", ".csv", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".zip", ".rar", ".7z",
            ".mp3", ".mp4"}
DANGEROUS_EXT = {".php", ".phtml", ".html", ".htm", ".js", ".exe", ".bat", ".sh", ".cmd",
                 ".msi", ".htaccess"}

errors, warns = [], []


def ok(msg):
    print("  OK    " + msg)


def warn(msg):
    print("  WARN  " + msg)
    warns.append(msg)


def err(msg):
    print("  ERROR " + msg)
    errors.append(msg)


def section(title):
    print("\n== " + title)


def disk_files():
    files = {}
    for root in (OUT_DIR, OUT_EXTRA):
        if root.exists():
            for p in root.rglob("*"):
                if p.is_file():
                    rel = p.relative_to(root).as_posix()
                    if rel in files:
                        err(f"same file in both output folders: {rel}")
                    files[rel] = p
    return files


def main():
    if not OUT_DIR.exists():
        sys.exit(f"Folder {OUT_DIR} not found. Run byyear.py first.")
    if not Path("announcements_new.csv").exists():
        sys.exit("announcements_new.csv not found. Run byyear.py first.")

    files = disk_files()

    # ------------------------------------------------------------------ CSV
    section("announcements_new.csv")
    with open("announcements_new.csv", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    needed = {"title", "old_slug", "slug", "date", "content", "year"}
    missing_cols = needed - set(rows[0].keys())
    if missing_cols:
        err(f"missing columns: {sorted(missing_cols)}")
    else:
        ok(f"{len(rows)} announcements, columns: {', '.join(rows[0].keys())}")

    if Path("announcements.csv").exists():
        with open("announcements.csv", encoding="utf-8-sig") as f:
            n_old = sum(1 for _ in csv.DictReader(f))
        (ok if n_old == len(rows) else err)(f"rows in announcements.csv: {n_old}, in announcements_new.csv: {len(rows)}")

    bad_date = [r["old_slug"] for r in rows if not re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", r["date"] or "")]
    (err if bad_date else ok)(f"dates with wrong format: {len(bad_date)}" + (f" e.g. {bad_date[:3]}" if bad_date else ""))
    bad_year = [r["old_slug"] for r in rows if (r["date"] or "")[:4] != r["year"]]
    (err if bad_year else ok)(f"year column different from the date: {len(bad_year)}")
    empty_title = [r["old_slug"] for r in rows if not (r["title"] or "").strip()]
    (err if empty_title else ok)(f"empty titles: {len(empty_title)}")
    empty_body = [r["old_slug"] for r in rows if not (r["content"] or "").strip()]
    (warn if empty_body else ok)(f"empty content: {len(empty_body)}")
    dup = [s for s, c in Counter(r["old_slug"] for r in rows).items() if c > 1]
    (err if dup else ok)(f"duplicate old_slug (would not import as separate posts): {len(dup)}" + (f" e.g. {dup[:3]}" if dup else ""))
    long_slug = [r["old_slug"] for r in rows if len(r["slug"]) > 200]
    (err if long_slug else ok)(f"slugs longer than 200 characters: {len(long_slug)}")
    years = Counter(r["year"] for r in rows)
    ok("announcements per year: " + ", ".join(f"{y}: {years[y]}" for y in sorted(years)))

    # ---------------------------------------------------------------- links
    section("links inside the announcements")
    referenced, unresolved, leftovers, tel_bad = set(), [], [], 0
    other_internal, external, scripts = set(), 0, 0
    for r in rows:
        html = r["content"]
        if "<script" in html.lower():
            scripts += 1
        if f"{SITE}/tel:" in html or f"{SITE}/mailto:" in html:
            tel_bad += 1
        soup = BeautifulSoup(html, "html.parser")
        for tag, attr in (("a", "href"), ("img", "src")):
            for el in soup.find_all(tag, attrs={attr: True}):
                v = el[attr].strip()
                if v.startswith(NEW_BASE):
                    rel = unquote(v[len(NEW_BASE):].split("#")[0].split("?")[0])
                    referenced.add(rel)
                    if rel not in files:
                        unresolved.append((r["old_slug"], rel))
                elif (v.startswith(SITE + OLD_MEDIA) or v.startswith(OLD_MEDIA)
                      or v.startswith(OLD_MEDIA.lstrip("/"))):
                    leftovers.append((r["old_slug"], v))
                elif v.startswith(SITE + "/"):
                    other_internal.add(v)
                elif v.startswith("http"):
                    external += 1

    (err if unresolved else ok)(f"links to year folders that do not exist on disk: {len(unresolved)}")
    for slug, rel in unresolved[:10]:
        print(f"          {slug}  ->  {rel}")
    (err if leftovers else ok)(f"links still pointing to the old media folder: {len(leftovers)}")
    for slug, v in leftovers[:10]:
        print(f"          {slug}  ->  {v}")
    (err if tel_bad else ok)(f"announcements with broken tel:/mailto: links: {tel_bad}")
    (warn if other_internal else ok)(f"links to other pages of {SITE} (fix by hand after the import): {len(other_internal)}")
    for u in sorted(other_internal)[:10]:
        print(f"          {u}")
    ok(f"links to external sites (left unchanged): {external}")
    (warn if scripts else ok)(f"announcements containing <script>: {scripts}")

    # ---------------------------------------------------------------- files
    section("files in the year folders")
    per_year = Counter(rel.split("/")[0] for rel in files)
    ok(f"{len(files)} files: " + ", ".join(f"{y}: {per_year[y]}" for y in sorted(per_year)))

    zero = [rel for rel, p in files.items() if p.stat().st_size == 0]
    (err if zero else ok)(f"empty (0 byte) files: {len(zero)}")
    for rel in zero[:10]:
        print(f"          {rel}")
    dangerous = [rel for rel in files if Path(rel).suffix.lower() in DANGEROUS_EXT]
    (err if dangerous else ok)(f"dangerous file types (php, html, js, exe...): {len(dangerous)}")
    for rel in dangerous[:10]:
        print(f"          {rel}")
    unusual = Counter(Path(rel).suffix.lower() or "(none)" for rel in files
                      if Path(rel).suffix.lower() not in SAFE_EXT | DANGEROUS_EXT)
    (warn if unusual else ok)("unusual file types: " + (", ".join(f"{e} x{c}" for e, c in unusual.items()) if unusual else "none"))
    orphans = sorted(set(files) - referenced)
    (warn if orphans else ok)(f"files not linked from any announcement: {len(orphans)}")
    for rel in orphans[:10]:
        print(f"          {rel}")
    non_ascii = [rel for rel in files if not rel.isascii()]
    (warn if non_ascii else ok)(f"files with non-ASCII (Greek) names: {len(non_ascii)}"
                                + (" -> upload with SFTP/scp, NOT in a zip" if non_ascii else ""))
    lower = Counter(rel.lower() for rel in files)
    case_pairs = [k for k, c in lower.items() if c > 1]
    (warn if case_pairs else ok)(f"names that differ only in letter case: {len(case_pairs)}"
                                 + (" (fine on Linux, never put them in one Windows folder)" if case_pairs else ""))
    if OUT_EXTRA.exists():
        warn(f"{OUT_EXTRA} exists: upload it to the SAME place as {OUT_DIR}")

    # ------------------------------------------------------------- manifest
    section("files_byyear.csv (manifest)")
    if not Path("files_byyear.csv").exists():
        err("files_byyear.csv not found")
    else:
        with open("files_byyear.csv", encoding="utf-8-sig") as f:
            man = list(csv.DictReader(f))
        (ok if len(man) == len(files) else err)(f"manifest rows: {len(man)}, files on disk: {len(files)}")
        wrong = 0
        for m in man:
            rel = unquote(m["path"][len(NEW_BASE):])
            p = files.get(rel)
            if p is None or p.stat().st_size != int(m["size"]):
                wrong += 1
        (err if wrong else ok)(f"manifest entries whose file is missing or has a different size: {wrong}")

    # ------------------------------------------------------------ redirects
    section("redirect files")
    ng, ap = Path("redirects_nginx.conf"), Path("redirects_apache.htaccess")
    if ng.exists():
        lines = ng.read_text(encoding="utf-8").splitlines()
        n = sum(1 for l in lines if l.startswith('location = "'))
        (ok if n == len(files) else warn)(f"nginx: {n} file rules for {len(files)} files")
        (ok if any(l.startswith("rewrite ") for l in lines) else err)("nginx: rule for the announcement URLs present")
    else:
        err("redirects_nginx.conf not found")
    if ap.exists():
        lines = ap.read_text(encoding="utf-8").splitlines()
        n = sum(1 for l in lines if l.startswith('RewriteRule "^' + OLD_MEDIA.lstrip("/")))
        (ok if n == len(files) else warn)(f"apache: {n} file rules for {len(files)} files")
    else:
        err("redirects_apache.htaccess not found")

    # --------------------------------------------------------------- result
    print(f"\nRESULT: {len(errors)} error(s), {len(warns)} warning(s)")
    if errors:
        print("Fix the errors before uploading anything.")
        sys.exit(1)
    print("No errors. Check the warnings, then upload.")


if __name__ == "__main__":
    main()
