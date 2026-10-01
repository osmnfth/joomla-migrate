import requests, hashlib, os, collections
from urllib.parse import urlparse, unquote

urls = [u.strip() for u in open("files.txt", encoding="utf-8") if u.strip()]
groups = collections.defaultdict(list)
for u in urls:
    groups[unquote(u).lower()].append(u)

for key, variants in groups.items():
    if len(variants) < 2:
        continue
    hashes = []
    for n, u in enumerate(variants, 1):
        data = requests.get(u, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
        status = data.status_code
        h = hashlib.sha256(data.content).hexdigest()[:12] if status == 200 else f"HTTP {status}"
        hashes.append(h)
        if status == 200:
            rel = unquote(urlparse(u).path).lstrip("/")
            dest = os.path.join("downloads_case", str(n), *rel.split("/"))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            open(dest, "wb").write(data.content)
        print(n, u, h)
    print("  ->", "ΙΔΙΟ ΠΕΡΙΕΧΟΜΕΝΟ" if len(set(hashes)) == 1 else "ΔΙΑΦΟΡΕΤΙΚΟ", "\n")
