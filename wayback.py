import requests
for line in open("failed.txt", encoding="utf-8"):
      u = line.split("\t")[0].strip()
      if not u:
          continue
      r = requests.get("https://archive.org/wayback/available", params={"url": u}, timeout=30).json()
      snap = r.get("archived_snapshots", {}).get("closest")
      print(u, "->", snap["url"] if snap else "NOT FOUND")