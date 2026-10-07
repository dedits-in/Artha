import os, re

d = "data/raw"
for f in sorted(os.listdir(d)):
    if not f.endswith(".txt") or f.startswith("fund_"):
        continue
    text = open(os.path.join(d, f), encoding="utf-8").read()
    name = re.search(r"Fund Name:\s*(.+)", text)
    cat = re.search(r"Scheme Category:\s*(.+)", text)
    print(f.ljust(30), "|", name.group(1).strip() if name else "-", "|", cat.group(1).strip() if cat else "-")