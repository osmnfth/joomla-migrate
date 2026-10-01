import csv, re
from urllib.parse import unquote
from bs4 import BeautifulSoup

OLD_PREFIX = "https://vo.duth.gr/images/"
NEW_PREFIX = "/wp-content/uploads/vo-archive/images/"
NOTE = " (το αρχείο δεν είναι πλέον διαθέσιμο)"

failed = {unquote(l.split("\t")[0].strip()) for l in open("failed.txt", encoding="utf-8") if l.strip()}

rows = list(csv.DictReader(open("announcements.csv", encoding="utf-8-sig")))
img_posts, other_links, removed = [], set(), 0

for r in rows:
    c = r["content"].replace("https://vo.duth.gr/tel:", "tel:")
    if "<img" in c:
        img_posts.append(r["old_slug"])
    for u in re.findall(r'href="(https://vo\.duth\.gr/[^"]+)"', c):
        if not u.startswith(OLD_PREFIX):
            other_links.add(u)

    soup = BeautifulSoup(c, "html.parser")
    for a in soup.find_all("a", href=True):
        if unquote(a["href"]) in failed:
            a.insert_after(NOTE)
            a.unwrap()
            removed += 1
    r["content"] = str(soup).replace(OLD_PREFIX, NEW_PREFIX)

with open("announcements_new.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader(); w.writerows(rows)

print("ανακοινώσεις:", len(rows))
print("με <img> μέσα:", len(img_posts))
print("σπασμένα links που αφαιρέθηκαν:", removed)
print("links προς vo.duth.gr εκτός /images/:", len(other_links))
for u in sorted(other_links)[:20]:
    print("  ", u)