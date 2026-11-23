import json, subprocess, random, time, urllib.parse
D = "/Users/penggenhui/.gemini/antigravity/brain/892d923c-0d1e-443e-8902-ca2f682c36c0/scratch/"
def get(url):
    for _ in range(3):
        try:
            return json.loads(subprocess.run(["curl", "-s", "--max-time", "30", "-A", "fish-probe/0.1", url], capture_output=True, text=True).stdout)
        except Exception:
            time.sleep(2)
    return None
keys = json.load(open(D + "cn_fish_species_keys.json"))
random.seed(7)
sample = random.sample(keys, 100)
out = []
for k in sample:
    sp = get(f"https://api.gbif.org/v1/species/{k}") or {}
    name = sp.get("canonicalName") or sp.get("scientificName", "")
    s = {"name": name, "family": sp.get("family")}
    t = get(f"https://api.inaturalist.org/v1/taxa?q={urllib.parse.quote(name)}&rank=species&per_page=1"); time.sleep(1.1)
    tid = t["results"][0]["id"] if t and t.get("results") and t["results"][0]["name"].lower() == name.lower() else None
    s["obs_open"] = s["obs_any"] = 0
    if tid:
        a = get(f"https://api.inaturalist.org/v1/observations?taxon_id={tid}&quality_grade=research&photo_license=cc0,cc-by,cc-by-sa&per_page=0"); time.sleep(1.1)
        b = get(f"https://api.inaturalist.org/v1/observations?taxon_id={tid}&photo_license=cc0,cc-by,cc-by-sa,cc-by-nc,cc-by-nc-sa,cc-by-nd,cc-by-nc-nd&per_page=0"); time.sleep(1.1)
        s["obs_open"] = (a or {}).get("total_results", 0); s["obs_any"] = (b or {}).get("total_results", 0)
    c = get("https://commons.wikimedia.org/w/api.php?action=query&list=search&srnamespace=6&format=json&srlimit=1&srsearch=" + urllib.parse.quote('"' + name + '"'))
    s["commons"] = c["query"]["searchinfo"]["totalhits"] if c else 0
    g = get(f"https://api.gbif.org/v1/occurrence/search?taxonKey={k}&mediaType=StillImage&license=CC0_1_0&license=CC_BY_4_0&limit=0")
    s["gbif_open"] = (g or {}).get("count", 0)
    out.append(s); print(json.dumps(s, ensure_ascii=False), flush=True)
json.dump(out, open(D + "cn_probe_result.json", "w"), ensure_ascii=False, indent=1)
n = len(out)
def pct(f):
    k = sum(1 for x in out if f(x)); return f"{k}/{n} = {100*k/n:.0f}%"
print("SUMMARY-CN")
print("iNat open research-grade >=1:", pct(lambda x: x["obs_open"] >= 1))
print("Commons >=1:", pct(lambda x: x["commons"] >= 1))
print("GBIF open img >=1:", pct(lambda x: x["gbif_open"] >= 1))
print("any open:", pct(lambda x: x["obs_open"] >= 1 or x["commons"] >= 1 or x["gbif_open"] >= 1))
print("any incl NC:", pct(lambda x: x["obs_open"] >= 1 or x["commons"] >= 1 or x["gbif_open"] >= 1 or x["obs_any"] >= 1))
