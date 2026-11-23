"""Pilot step 1: fetch reference images for the 30 pilot species.
Images are stored OUTSIDE the repo (scratch/pilot/refs). Only metadata is kept for the project."""
import json, subprocess, time, os, urllib.parse
ROOT = "/Users/penggenhui/.gemini/antigravity/brain/892d923c-0d1e-443e-8902-ca2f682c36c0/scratch/pilot"
os.makedirs(ROOT + "/refs", exist_ok=True)

PILOT = [
 # (scientific name, zh, view, planned tier)
 ("Amphiprion ocellaris", "眼斑双锯鱼", "lateral", "A"),
 ("Oncorhynchus mykiss", "虹鳟", "lateral", "A"),
 ("Cyprinus carpio", "鲤", "lateral", "A"),
 ("Siniperca chuatsi", "鳜", "lateral", "A"),
 ("Larimichthys crocea", "大黄鱼", "lateral", "A"),
 ("Pterois volitans", "斑鳍蓑鲉", "lateral", "A"),
 ("Chaetodon auriga", "丝蝴蝶鱼", "lateral", "A"),
 ("Thalassoma lunare", "新月锦鱼", "lateral", "A"),
 ("Betta splendens", "五彩搏鱼", "lateral", "A"),
 ("Silurus asotus", "鲇", "lateral", "A"),
 ("Gadus morhua", "大西洋鳕", "lateral", "A"),
 ("Thunnus albacares", "黄鳍金枪鱼", "lateral", "A"),
 ("Carcharodon carcharias", "噬人鲨", "lateral", "A"),
 ("Sphyrna lewini", "路氏双髻鲨", "lateral", "A"),
 ("Paralichthys olivaceus", "牙鲆", "eyed-side", "A"),
 ("Hemitrygon akajei", "赤魟", "dorsal", "A"),
 ("Hippocampus kuda", "管海马", "vertical", "A"),
 ("Anguilla japonica", "日本鳗鲡", "lateral", "A"),
 ("Lophius litulon", "黄鮟鱇", "lateral", "A"),
 ("Takifugu rubripes", "红鳍东方鲀", "lateral", "A"),
 ("Ostracion cubicus", "粒突箱鲀", "lateral", "A"),
 ("Mola mola", "翻车鲀", "lateral", "A"),
 ("Latimeria chalumnae", "矛尾鱼", "lateral", "A"),
 ("Lethenteron camtschaticum", "日本七鳃鳗", "lateral", "A"),
 ("Acipenser sinensis", "中华鲟", "lateral", "A"),
 ("Myxocyprinus asiaticus", "胭脂鱼", "lateral", "A"),
 ("Neocentropogon japonicus", "日本新鳞鲉", "lateral", "C"),
 ("Hemigobius mingi", "", "lateral", "C"),
 ("Pentapodus berryae", "", "lateral", "D"),
 ("Johnius hypostoma", "", "lateral", "D"),
]
OPEN = {"cc0", "cc-by", "cc-by-sa"}

def get(url):
    for _ in range(3):
        try:
            return json.loads(subprocess.run(["curl", "-s", "--max-time", "30", "-A", "fish-pilot/0.1", url],
                                             capture_output=True, text=True).stdout)
        except Exception:
            time.sleep(2)
    return None

def dl(url, path):
    subprocess.run(["curl", "-s", "-L", "--max-time", "60", "-o", path, url])
    return os.path.exists(path) and os.path.getsize(path) > 5000

manifest = []
for name, zh, view, plan in PILOT:
    sid = name.replace(" ", "_")
    d = f"{ROOT}/refs/{sid}"; os.makedirs(d, exist_ok=True)
    rec = {"id": sid, "scientificName": name, "zh": zh, "view": view, "plannedTier": plan, "refs": []}
    if plan == "A":
        t = get(f"https://api.inaturalist.org/v1/taxa?q={urllib.parse.quote(name)}&rank=species&per_page=1"); time.sleep(1)
        tid = t["results"][0]["id"] if t and t.get("results") else None
        rec["inat_taxon"] = tid
        for lic_set, tier in ((",".join(OPEN), "A"), ("cc-by-nc,cc-by-nc-sa,cc-by-nd,cc-by-nc-nd", "B")):
            if len(rec["refs"]) >= 3 or not tid: break
            o = get(f"https://api.inaturalist.org/v1/observations?taxon_id={tid}&quality_grade=research&photo_license={lic_set}&order_by=votes&per_page=15"); time.sleep(1)
            for ob in (o or {}).get("results", []):
                for p in ob.get("photos", [])[:1]:
                    if p.get("license_code") not in lic_set.split(","): continue
                    url = p["url"].replace("square", "large")
                    fn = f"{d}/ref{len(rec['refs'])+1}.jpg"
                    if dl(url, fn):
                        rec["refs"].append({"file": fn, "tier": tier, "license": p["license_code"],
                                            "attribution": p.get("attribution"),
                                            "page": f"https://www.inaturalist.org/observations/{ob['id']}"})
                if len(rec["refs"]) >= 3: break
    elif plan == "C":
        m = get(f"https://api.gbif.org/v1/species/match?name={urllib.parse.quote(name)}")
        key = m.get("usageKey")
        o = get(f"https://api.gbif.org/v1/occurrence/search?taxonKey={key}&mediaType=StillImage&license=CC0_1_0&license=CC_BY_4_0&limit=10")
        for oc in (o or {}).get("results", []):
            for med in oc.get("media", []):
                if med.get("type") != "StillImage" or not med.get("identifier"): continue
                fn = f"{d}/ref{len(rec['refs'])+1}.jpg"
                if dl(med["identifier"], fn):
                    rec["refs"].append({"file": fn, "tier": "C", "license": oc.get("license"),
                                        "attribution": med.get("rightsHolder") or oc.get("institutionCode"),
                                        "basisOfRecord": oc.get("basisOfRecord"),
                                        "page": f"https://www.gbif.org/occurrence/{oc['key']}"})
                break
            if len(rec["refs"]) >= 2: break
    tiers = [r["tier"] for r in rec["refs"]]
    rec["tier"] = "A" if "A" in tiers else "B" if "B" in tiers else "C" if "C" in tiers else "D"
    manifest.append(rec)
    print(sid, rec["tier"], len(rec["refs"]), flush=True)
json.dump(manifest, open(ROOT + "/manifest.json", "w"), ensure_ascii=False, indent=1)
