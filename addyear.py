import csv, sys

path = sys.argv[1] if len(sys.argv) > 1 else "announcements_new.csv"
with open(path, encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

for r in rows:
    r["year"] = r["date"][:4]

fields = list(rows[0].keys())
with open(path, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

years = sorted({r["year"] for r in rows})
print(len(rows), "rows, years:", years[0], "-", years[-1])