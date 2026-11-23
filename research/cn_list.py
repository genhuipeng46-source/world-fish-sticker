import json, subprocess, random, time
D = "/Users/penggenhui/.gemini/antigravity/brain/892d923c-0d1e-443e-8902-ca2f682c36c0/scratch/"
def get(url):
    for _ in range(3):
        try:
            return json.loads(subprocess.run(["curl", "-s", "--max-time", "60", url], capture_output=True, text=True).stdout)
        except Exception:
            time.sleep(2)
    return None
NONFISH_CLASSES = {"Aves", "Mammalia", "Reptilia", "Amphibia", "Squamata", "Testudines", "Crocodylia",
                   "Ascidiacea", "Thaliacea", "Appendicularia", "Leptocardii"}
o = get("https://api.gbif.org/v1/occurrence/search?country=CN&phylumKey=44&limit=0&facet=orderKey&orderKey.facetLimit=1000")
orders = [c["name"] for c in o["facets"][0]["counts"]]
fish_orders = []
for k in orders:
    sp = get(f"https://api.gbif.org/v1/species/{k}")
    cls = sp.get("class")
    if cls in NONFISH_CLASSES or sp.get("kingdom") != "Animalia":
        continue
    if cls is None or cls in ("Elasmobranchii", "Holocephali", "Myxini", "Petromyzonti", "Actinopterygii", "Sarcopterygii", "Dipneusti", "Actinistia"):
        fish_orders.append((k, sp.get("canonicalName"), cls))
print("fish orders in CN:", len(fish_orders), [x[1] for x in fish_orders][:80])
species = set()
for k, name, cls in fish_orders:
    f = get(f"https://api.gbif.org/v1/occurrence/search?country=CN&orderKey={k}&limit=0&facet=speciesKey&speciesKey.facetLimit=5000")
    for c in f["facets"][0]["counts"] if f and f.get("facets") else []:
        species.add(int(c["name"]))
print("species with GBIF records in China:", len(species))
json.dump(sorted(species), open(D + "cn_fish_species_keys.json", "w"))
