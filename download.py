import requests, os, time
from urllib.parse import urlparse, unquote

HEAD = {"User-Agent": "Mozilla/5.0"}
urls = [u.strip() for u in open("files.txt", encoding="utf-8") if u.strip()]
failed = []

for n, u in enumerate(urls, 1):
    rel = unquote(urlparse(u).path).lstrip("/")
    dest = os.path.join("downloads", *rel.split("/"))
    if os.path.exists(dest):
        continue
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    try:
        r = requests.get(u, headers=HEAD, timeout=60)
        r.raise_for_status()
        open(dest, "wb").write(r.content)
    except Exception as e:
        failed.append(f"{u}\t{e}")
    print(n, "/", len(urls))
    time.sleep(0.5)

open("failed.txt", "w", encoding="utf-8").write("\n".join(failed))
print("τέλος, αποτυχίες:", len(failed))