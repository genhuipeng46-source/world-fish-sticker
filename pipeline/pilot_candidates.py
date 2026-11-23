"""Pilot step 1b: fetch up to 10 candidate photos per A/B species and build a numbered contact sheet,
so a vision model can pick the clearest lateral views (most-voted photos are often frontal/blurry)."""
import json, subprocess, time, os
from PIL import Image, ImageDraw
ROOT = "/Users/penggenhui/.gemini/antigravity/brain/892d923c-0d1e-443e-8902-ca2f682c36c0/scratch/pilot"
OPEN = "cc0,cc-by,cc-by-sa"; NC = "cc-by-nc,cc-by-nc-sa,cc-by-nd,cc-by-nc-nd"
def get(url):
    for _ in range(3):
        try:
            return json.loads(subprocess.run(["curl", "-s", "--max-time", "30", "-A", "fish-pilot/0.1", url], capture_output=True, text=True).stdout)
        except Exception:
            time.sleep(2)
def dl(url, path):
    subprocess.run(["curl", "-s", "-L", "--max-time", "60", "-o", path, url])
    return os.path.exists(path) and os.path.getsize(path) > 5000
man = json.load(open(ROOT + "/manifest.json"))
os.makedirs(ROOT + "/sheets", exist_ok=True)
for rec in man:
    tid = rec.get("inat_taxon")
    if not tid: continue
    d = f"{ROOT}/cand/{rec['id']}"; os.makedirs(d, exist_ok=True)
    cands = []
    for lic, tier in ((OPEN, "A"), (NC, "B")):
        if len(cands) >= 10: break
        o = get(f"https://api.inaturalist.org/v1/observations?taxon_id={tid}&quality_grade=research&photo_license={lic}&order_by=votes&per_page=40"); time.sleep(1)
        for ob in (o or {}).get("results", []):
            for p in ob.get("photos", [])[:2]:
                if p.get("license_code") not in lic.split(","): continue
                fn = f"{d}/c{len(cands)+1:02d}.jpg"
                if dl(p["url"].replace("square", "large"), fn):
                    cands.append({"n": len(cands)+1, "file": fn, "tier": tier, "license": p["license_code"],
                                  "attribution": p.get("attribution"), "page": f"https://www.inaturalist.org/observations/{ob['id']}"})
                if len(cands) >= 10: break
            if len(cands) >= 10: break
    rec["candidates"] = cands
    # contact sheet 5x2, 360x240 cells
    W, H = 360, 240
    sheet = Image.new("RGB", (W * 5, H * 2), "white"); dr = ImageDraw.Draw(sheet)
    for c in cands:
        try:
            im = Image.open(c["file"]).convert("RGB"); im.thumbnail((W, H))
        except Exception:
            continue
        i = c["n"] - 1; x, y = (i % 5) * W, (i // 5) * H
        sheet.paste(im, (x, y)); dr.rectangle([x, y, x + 46, y + 26], fill="black")
        dr.text((x + 6, y + 6), f"{c['n']}{c['tier']}", fill="yellow")
    sheet.save(f"{ROOT}/sheets/{rec['id']}.jpg", quality=80)
    print(rec["id"], len(cands), flush=True)
json.dump(man, open(ROOT + "/manifest.json", "w"), ensure_ascii=False, indent=1)
