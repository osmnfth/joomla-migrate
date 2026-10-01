import requests, csv, re, time
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse, unquote
from bs4 import BeautifulSoup

FEED = "https://vo.duth.gr/index.php/el/anakoinoseis"
HEAD = {"User-Agent": "Mozilla/5.0"}
seen, rows, start = set(), [], 0

def clean(html):
    s = BeautifulSoup(html, "html.parser")
    for h in s.find_all("h1"):
        h.unwrap()
    for a in s.find_all("a"):
        if not a.get_text(strip=True) and not a.find("img"):
            a.decompose()
        else:
            a.attrs.pop("download", None)
            a.attrs.pop("target", None)
    for t in s.find_all(True):
        t.attrs.pop("class", None)
        t.attrs.pop("id", None)
    return str(s).replace("&nbsp;", " ")

while True:
    r = requests.get(FEED, params={"format": "feed", "type": "rss", "start": start}, headers=HEAD)
    items = ET.fromstring(r.content).findall("./channel/item")
    if not items:
        break
    for i in items:
        link = i.findtext("link")
        if link in seen:
            continue
        seen.add(link)
        slug = unquote(urlparse(link).path.rsplit("/", 1)[-1])
        rows.append({
            "title": (i.findtext("title") or "").strip(),
            "old_slug": slug,
            "slug": slug[:200],
            "date": parsedate_to_datetime(i.findtext("pubDate")).strftime("%Y-%m-%d %H:%M:%S"),
            "content": clean(i.findtext("description") or ""),
        })
    start += len(items)
    print("fetched", len(rows))
    time.sleep(1)

with open("announcements.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=["title", "old_slug", "slug", "date", "content"])
    w.writeheader(); w.writerows(rows)

from urllib.parse import quote
files = set()
for x in rows:
    files.update(re.findall(r'(?:href|src)="(https://vo\.duth\.gr/images/[^"]+)"', x["content"]))
files = {quote(u, safe=":/%?=&") for u in files}
open("files.txt", "w", encoding="utf-8").write("\n".join(sorted(files)))