import json, subprocess, time, urllib.parse
D = "/Users/penggenhui/.gemini/antigravity/brain/892d923c-0d1e-443e-8902-ca2f682c36c0/scratch/"
def get(url):
    for _ in range(3):
        try:
            return json.loads(subprocess.run(["curl", "-s", "--max-time", "30", url], capture_output=True, text=True).stdout)
        except Exception:
            time.sleep(2)
    return None
d = json.load(open(D + "ref_probe_result.json"))
for s in d:
    n = urllib.parse.quote(s["name"])
    m = get(f"https://api.gbif.org/v1/species/match?name={n}&kingdom=Animalia")
    key = m.get("usageKey") if m and m.get("matchType") in ("EXACT",) else None
    s["gbif_key"] = key
    s["gbif_img_open"] = s["gbif_img_any"] = 0
    if key:
        a = get(f"https://api.gbif.org/v1/occurrence/search?taxonKey={key}&mediaType=StillImage&license=CC0_1_0&license=CC_BY_4_0&limit=0")
        b = get(f"https://api.gbif.org/v1/occurrence/search?taxonKey={key}&mediaType=StillImage&limit=0")
        s["gbif_img_open"] = a.get("count", 0) if a else 0
        s["gbif_img_any"] = b.get("count", 0) if b else 0
    # Biodiversity Literature Repository (Zenodo) figures
    z = get("https://zenodo.org/api/records?communities=biosyslit&type=image&size=1&q=" + urllib.parse.quote('"' + s["name"] + '"'))
    s["blr_figs"] = z["hits"]["total"] if z and "hits" in z else None
    print(s["name"], s["gbif_img_open"], s["gbif_img_any"], s["blr_figs"], flush=True)
    time.sleep(0.5)
json.dump(d, open(D + "ref_probe_result2.json", "w"), ensure_ascii=False, indent=1)
n = len(d)
def pct(f):
    k = sum(1 for x in d if f(x)); return f"{k}/{n} = {100*k/n:.0f}%"
inat_or_commons = lambda x: x["obs_open"] >= 1 or (x["commons_files"] or 0) >= 1
print("SUMMARY2")
print("GBIF open (CC0/CC BY) images:", pct(lambda x: x["gbif_img_open"] >= 1))
print("GBIF any images:", pct(lambda x: x["gbif_img_any"] >= 1))
print("BLR figures:", pct(lambda x: (x["blr_figs"] or 0) >= 1))
print("previously nothing, now GBIF-open or BLR:", pct(lambda x: x["obs_any"] == 0 and not x["commons_files"] and (x["gbif_img_open"] >= 1 or (x["blr_figs"] or 0) >= 1)))
print("ANY open source (iNat-open/Commons/GBIF-open/BLR):", pct(lambda x: inat_or_commons(x) or x["gbif_img_open"] >= 1 or (x["blr_figs"] or 0) >= 1))
print("still nothing usable:", pct(lambda x: not (inat_or_commons(x) or x["gbif_img_open"] >= 1 or (x["blr_figs"] or 0) >= 1 or x["obs_any"] >= 1)))
