import json, random, time, urllib.request, urllib.parse, sys
K = 317005
UA = {"User-Agent": "fish-sticker-feasibility-probe/0.1"}
import subprocess
def get(url):
    for i in range(3):
        try:
            out = subprocess.run(["curl", "-s", "--max-time", "30", "-A", UA["User-Agent"], url],
                                 capture_output=True, text=True).stdout
            return json.loads(out)
        except Exception as e:
            time.sleep(2)
    return None

roots = {"8VR36": 36672, "LB": 1303, "CK": 59, "6225G": 93, "8VJWX": 49}
total = sum(roots.values())
random.seed(42)
N = int(sys.argv[1]) if len(sys.argv) > 1 else 150
sample = []
while len(sample) < N:
    r = random.randrange(total)
    for rid, n in roots.items():
        if r < n: break
        r -= n
    d = get(f"https://api.checklistbank.org/dataset/{K}/nameusage/search?TAXON_ID={rid}&rank=species&status=accepted&limit=1&offset={r}")
    if not d or not d.get("result"): continue
    u = d["result"][0]["usage"]
    cls = [c["name"] for c in d["result"][0].get("classification", []) if c.get("rank") in ("family",)]
    sample.append({"name": u["name"]["scientificName"], "family": cls[0] if cls else "", "extinct": u.get("extinct")})
    time.sleep(0.2)

OPEN = "cc0,cc-by,cc-by-sa"
ALL = "cc0,cc-by,cc-by-sa,cc-by-nc,cc-by-nc-sa,cc-by-nd,cc-by-nc-nd"
out = []
for s in sample:
    q = urllib.parse.quote(s["name"])
    t = get(f"https://api.inaturalist.org/v1/taxa?q={q}&rank=species&per_page=1")
    time.sleep(1.1)
    tid = None
    if t and t.get("results") and t["results"][0]["name"].lower() == s["name"].lower():
        tid = t["results"][0]["id"]
    s["inat_id"] = tid
    s["obs_open"] = s["obs_any"] = 0
    if tid:
        a = get(f"https://api.inaturalist.org/v1/observations?taxon_id={tid}&quality_grade=research&photo_license={OPEN}&per_page=0")
        time.sleep(1.1)
        b = get(f"https://api.inaturalist.org/v1/observations?taxon_id={tid}&photo_license={ALL}&per_page=0")
        time.sleep(1.1)
        s["obs_open"] = a.get("total_results", 0) if a else 0
        s["obs_any"] = b.get("total_results", 0) if b else 0
    # Wikimedia Commons: category or file search
    c = get("https://commons.wikimedia.org/w/api.php?action=query&list=search&srnamespace=6&format=json&srlimit=1&srsearch=" + urllib.parse.quote('"' + s["name"] + '"'))
    s["commons_files"] = c["query"]["searchinfo"]["totalhits"] if c else None
    out.append(s)
    print(json.dumps(s, ensure_ascii=False), flush=True)

json.dump(out, open(__file__.replace("ref_probe.py", "ref_probe_result.json"), "w"), ensure_ascii=False, indent=1)
n = len(out)
def pct(f): return f"{sum(1 for x in out if f(x))}/{n} = {100*sum(1 for x in out if f(x))/n:.0f}%"
print("SUMMARY")
print("iNat taxon found:", pct(lambda x: x["inat_id"]))
print(">=1 research-grade open-license (CC0/BY/BY-SA) obs:", pct(lambda x: x["obs_open"] >= 1))
print(">=3 research-grade open-license obs:", pct(lambda x: x["obs_open"] >= 3))
print(">=1 any-CC obs:", pct(lambda x: x["obs_any"] >= 1))
print(">=1 Commons file:", pct(lambda x: (x["commons_files"] or 0) >= 1))
print("open iNat OR Commons:", pct(lambda x: x["obs_open"] >= 1 or (x["commons_files"] or 0) >= 1))
print("nothing at all:", pct(lambda x: x["obs_any"] == 0 and not x["commons_files"]))
