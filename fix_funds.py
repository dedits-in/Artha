import re
import shutil
from pathlib import Path

raw = Path("data/raw")
quarantine = Path("data/quarantine")
quarantine.mkdir(parents=True, exist_ok=True)

sources = sorted(list(raw.glob("*.txt")) + list(quarantine.glob("*.txt")))
for f in sources:
    in_raw = f.parent == raw
    if f.name.startswith("fund_"):
        continue
    if in_raw and re.match(r"\d", f.name):
        continue  # already named by scheme code

    text = f.read_text(encoding="utf-8")
    code_m = re.search(r"Scheme Code\s*:\s*(\d+)", text)
    name_m = re.search(r"Fund Name\s*:\s*(.+)", text)
    cat_m = re.search(r"Scheme Category\s*:\s*(.+)", text)
    code = int(code_m.group(1)) if code_m else 0
    name = name_m.group(1).strip() if name_m else None
    cat = cat_m.group(1).strip() if cat_m else "-"

    if not code or not name:
        print(f"EMPTY      {f.name:32} -> quarantine")
        if in_raw:
            shutil.move(str(f), quarantine / f.name)
        continue

    target = raw / f"{code}.txt"
    if target.exists():
        print(f"DUPLICATE  {f.name:32} -> {code} already exists ({name})")
        if in_raw:
            shutil.move(str(f), quarantine / f"dup_{f.name}")
        continue

    shutil.move(str(f), target)
    print(f"RENAMED    {f.name:32} -> {code}.txt | {name} | {cat}")