import json
import os

RAW_PATH = os.path.join(os.path.dirname(__file__), "raw")

for filename in os.listdir(RAW_PATH):
    if not filename.endswith(".json"):
        continue

    filepath = os.path.join(RAW_PATH, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    scheme = data.get("meta", {})
    nav_data = data.get("data", [])[:24]  # last 24 NAV entries

    text_content = f"""
Fund Name: {scheme.get('scheme_name', filename)}
Fund House: {scheme.get('fund_house', 'N/A')}
Scheme Type: {scheme.get('scheme_type', 'N/A')}
Scheme Category: {scheme.get('scheme_category', 'N/A')}

Recent NAV History (last 24 entries):
"""
    for entry in nav_data:
        text_content += f"  Date: {entry['date']} | NAV: ₹{entry['nav']}\n"

    txt_filename = filename.replace(".json", ".txt")
    txt_filepath = os.path.join(RAW_PATH, txt_filename)
    with open(txt_filepath, "w", encoding="utf-8") as f:
        f.write(text_content)

    print(f"Converted {filename} → {txt_filename}")

print("\nAll done! .txt files created in data/raw/")