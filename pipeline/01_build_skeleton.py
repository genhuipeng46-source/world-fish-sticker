#!/usr/bin/env python3
"""M1: Build the global fish species data skeleton from open-licensed sources.
Sources:
  - Catalogue of Life (dataset 317005, 2026-11-11, CC BY 4.0) -> taxonomy, authority, environments, extinct flag
  - Wikidata (CC0) -> external IDs (FishBase, GBIF, WoRMS, iNaturalist), IUCN status, multilingual names, zhwiki URL
  - GBIF (CC0/CC BY) -> China occurrence species list (for v1.0 launch tagging)
"""
import csv
import gzip
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import urllib.parse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

REPO = "/Users/penggenhui/GitHub项目/world-fish-sticker"
CACHE = f"{REPO}/pipeline/cache"
DATA = f"{REPO}/data"
os.makedirs(CACHE, exist_ok=True)
os.makedirs(f"{DATA}/species", exist_ok=True)

COL_DATASET = 317005
COL_VERSION = "2026-11-11"
COL_ROOTS = [
    ("8VR36", "Actinopterygii"),
    ("LB", "Elasmobranchii"),
    ("CK", "Holocephali"),
    ("6225G", "Myxini"),
    ("8VJWX", "Petromyzonti"),
    ("VSPGJ", "Dipnoi"),
    ("VSNN8", "Actinistia"),
]

IUCN_MAP = {
    "Q211005": "LC",
    "Q719675": "NT",
    "Q278113": "VU",
    "Q11394": "EN",
    "Q219127": "CR",
    "Q239509": "EW",
    "Q237350": "EX",
    "Q3245245": "DD",
    "Q3350324": "NE",
}

DORSAL_ORDERS = {"Myliobatiformes", "Rajiformes", "Torpediniformes", "Rhinopristiformes"}
DORSAL_FAMILIES = {"Lophiidae", "Ogcocephalidae", "Squatinidae"}

# Iconic global aquarium / economic / flagship species to always include in v1.0 alongside China species
FLAGSHIP_V1 = {
    "Amphiprion ocellaris", "Amphiprion percula", "Paracanthurus hepatus", "Zebrasoma flavescens",
    "Pterois volitans", "Chaetodon auriga", "Thalassoma lunare", "Betta splendens",
    "Paracheirodon innesi", "Pterophyllum scalare", "Symphysodon discus", "Poecilia reticulata",
    "Danio rerio", "Carassius auratus", "Cyprinus carpio", "Oncorhynchus mykiss",
    "Salmo salar", "Gadus morhua", "Thunnus albacares", "Thunnus thynnus",
    "Carcharodon carcharias", "Rhincodon typus", "Sphyrna lewini", "Manta birostris",
    "Mobula birostris", "Mola mola", "Latimeria chalumnae", "Arapaima gigas",
    "Electrophorus electricus", "Pygocentrus nattereri", "Hippocampus kuda", "Ostracion cubicus",
    "Synchiropus splendidus", "Chelmon rostratus", "Pomacanthus imperator", "Balistoides conspicillum",
}


def curl_json(url, accept="application/json", retries=4):
    for attempt in range(retries):
        p = subprocess.run(
            ["curl", "-s", "-f", "--max-time", "90", "-H", f"Accept: {accept}",
             "-A", "world-fish-sticker/0.1 (https://github.com/world-fish-sticker)", url],
            capture_output=True, text=True
        )
        if p.returncode == 0 and p.stdout.strip():
            try:
                return json.loads(p.stdout)
            except json.JSONDecodeError:
                pass
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch JSON: {url[:140]}")


def sparql(query):
    url = "https://query.wikidata.org/sparql?query=" + urllib.parse.quote(query)
    d = curl_json(url, accept="application/sparql-results+json", retries=4)
    return d["results"]["bindings"]


# ---------- Stage 1: Catalogue of Life ----------
def fetch_col():
    out = f"{CACHE}/col_fish.json"
    if os.path.exists(out):
        data = json.load(open(out))
        print(f"[COL] Loaded cached {len(data)} species")
        return data

    records = {}
    for root_id, root_class in COL_ROOTS:
        offset = 0
        limit = 1000
        total = None
        while total is None or offset < total:
            url = (f"https://api.checklistbank.org/dataset/{COL_DATASET}/nameusage/search"
                   f"?TAXON_ID={root_id}&rank=species&status=accepted&limit={limit}&offset={offset}")
            d = curl_json(url)
            total = d.get("total", 0)
            res = d.get("result", [])
            if not res:
                break
            for item in res:
                u = item["usage"]
                nm = u["name"]
                sci = nm.get("scientificName", "").strip()
                if not sci or " " not in sci:
                    continue
                cls_map = {c.get("rank"): c.get("name") for c in item.get("classification", [])}
                order = cls_map.get("order") or "Incertae_sedis"
                family = cls_map.get("family") or "Incertae_sedis"
                genus = nm.get("genus") or cls_map.get("genus") or sci.split()[0]
                link = u.get("link") or nm.get("link") or ""
                m_worms = re.search(r"aphia\.php\?p=taxdetails&id=(\d+)", link)
                rec = {
                    "colId": u["id"],
                    "scientificName": sci,
                    "authority": nm.get("authorship") or "",
                    "class": root_class,
                    "order": order,
                    "family": family,
                    "genus": genus,
                    "environments": sorted(set(u.get("environments") or [])),
                    "extinct": bool(u.get("extinct")),
                    "wormsFromCol": int(m_worms.group(1)) if m_worms else None,
                }
                records[sci] = rec
            offset += len(res)
            print(f"  [COL] {root_class}: {min(offset, total)}/{total}", flush=True)
            time.sleep(0.15)
    data = list(records.values())
    json.dump(data, open(out, "w"), ensure_ascii=False)
    print(f"[COL] Saved {len(data)} unique accepted fish species")
    return data


# ---------- Stage 2: Wikidata (CC0) ----------
def fetch_wikidata():
    out = f"{CACHE}/wikidata_fish.json"
    if os.path.exists(out):
        d = json.load(open(out))
        print(f"[WD] Loaded cached {len(d)} Wikidata fish items")
        return d

    by_name = {}

    def ensure(sci, qid):
        if sci not in by_name:
            by_name[sci] = {"wikidata": qid, "ids": {}, "names": {}, "zh": {}, "iucn": None}
        return by_name[sci]

    print("[WD] Query 1/4: external IDs & IUCN...", flush=True)
    rows = sparql("""
        SELECT ?item ?name ?fb ?gbif ?worms ?inat ?iucn WHERE {
          ?item wdt:P938 ?fb ; wdt:P225 ?name .
          OPTIONAL { ?item wdt:P846 ?gbif }
          OPTIONAL { ?item wdt:P850 ?worms }
          OPTIONAL { ?item wdt:P3151 ?inat }
          OPTIONAL { ?item wdt:P141 ?iucn }
        }
    """)
    qid_to_sci = {}
    for r in rows:
        sci = r["name"]["value"].strip()
        qid = r["item"]["value"].rsplit("/", 1)[-1]
        qid_to_sci[qid] = sci
        rec = ensure(sci, qid)
        if "fb" in r: rec["ids"]["fishbase"] = int(r["fb"]["value"]) if r["fb"]["value"].isdigit() else r["fb"]["value"]
        if "gbif" in r: rec["ids"]["gbif"] = r["gbif"]["value"]
        if "worms" in r: rec["ids"]["worms"] = int(r["worms"]["value"]) if r["worms"]["value"].isdigit() else r["worms"]["value"]
        if "inat" in r: rec["ids"]["inaturalist"] = int(r["inat"]["value"]) if r["inat"]["value"].isdigit() else r["inat"]["value"]
        if "iucn" in r:
            iq = r["iucn"]["value"].rsplit("/", 1)[-1]
            if iq in IUCN_MAP:
                rec["iucn"] = IUCN_MAP[iq]
    print(f"  -> {len(by_name)} species matched via P938", flush=True)

    print("[WD] Query 2/4: Chinese labels (zh-hans, zh-cn, zh, zh-hant, zh-tw)...", flush=True)
    rows = sparql("""
        SELECT ?item ?lang ?label WHERE {
          ?item wdt:P938 ?fb .
          ?item rdfs:label ?label .
          BIND(LANG(?label) AS ?lang)
          FILTER(?lang IN ("zh-hans","zh-cn","zh","zh-hant","zh-tw"))
        }
    """)
    zh_buckets = defaultdict(dict)
    for r in rows:
        qid = r["item"]["value"].rsplit("/", 1)[-1]
        lang = r["lang"]["value"]
        val = r["label"]["value"].strip()
        if re.search(r"[\u4e00-\u9fff]", val):
            zh_buckets[qid][lang] = val
    for qid, m in zh_buckets.items():
        sci = qid_to_sci.get(qid)
        if not sci: continue
        rec = by_name[sci]
        zh_hans = m.get("zh-cn") or m.get("zh-hans") or m.get("zh")
        zh_hant = m.get("zh-hant") or m.get("zh-tw")
        if zh_hans: rec["names"]["zh-Hans"] = zh_hans
        if zh_hant: rec["names"]["zh-Hant"] = zh_hant
        aliases = [v for k, v in m.items() if v and v != zh_hans]
        if aliases:
            rec["zh"]["aliases"] = sorted(set(aliases))

    print("[WD] Query 3/4: English common names (P1843) & major multilingual labels...", flush=True)
    rows = sparql("""
        SELECT ?item ?c WHERE {
          ?item wdt:P938 ?fb ; wdt:P1843 ?c .
          FILTER(LANG(?c) = "en")
        }
    """)
    for r in rows:
        qid = r["item"]["value"].rsplit("/", 1)[-1]
        sci = qid_to_sci.get(qid)
        if sci and "en" not in by_name[sci]["names"]:
            by_name[sci]["names"]["en"] = r["c"]["value"].strip()

    for lang in ("ja", "ko", "fr", "de", "es", "pt", "ru"):
        rows = sparql(f"""
            SELECT ?item ?l WHERE {{
              ?item wdt:P938 ?fb ; rdfs:label ?l .
              FILTER(LANG(?l) = "{lang}")
            }}
        """)
        for r in rows:
            qid = r["item"]["value"].rsplit("/", 1)[-1]
            sci = qid_to_sci.get(qid)
            if not sci: continue
            val = r["l"]["value"].strip()
            # skip labels identical to scientific name
            if val.lower() != sci.lower():
                by_name[sci]["names"][lang] = val
        time.sleep(0.5)

    print("[WD] Query 4/4: Chinese Wikipedia URLs...", flush=True)
    rows = sparql("""
        SELECT ?item ?article WHERE {
          ?item wdt:P938 ?fb .
          ?article schema:about ?item ; schema:isPartOf <https://zh.wikipedia.org/> .
        }
    """)
    for r in rows:
        qid = r["item"]["value"].rsplit("/", 1)[-1]
        sci = qid_to_sci.get(qid)
        if sci:
            by_name[sci]["zh"]["wikipedia"] = r["article"]["value"]

    json.dump(by_name, open(out, "w"), ensure_ascii=False)
    print(f"[WD] Saved {len(by_name)} records")
    return by_name


# ---------- Stage 3: China Fish Species Names ----------
def fetch_china_names(wd_by_name):
    out = f"{CACHE}/cn_species_names.json"
    if os.path.exists(out):
        s = set(json.load(open(out)))
        print(f"[CN] Loaded cached {len(s)} China species names")
        return s

    keys = json.load(open(f"{REPO}/research/cn_fish_species_keys.json"))
    gbif_to_sci = {str(v["ids"]["gbif"]): sci for sci, v in wd_by_name.items() if v["ids"].get("gbif")}
    cn_names = set()
    missing = []
    for k in keys:
        sci = gbif_to_sci.get(str(k))
        if sci:
            cn_names.add(sci)
        else:
            missing.append(k)
    print(f"[CN] Matched {len(cn_names)}/{len(keys)} via Wikidata GBIF IDs; fetching {len(missing)} remaining from GBIF API...", flush=True)

    def resolve(k):
        try:
            d = curl_json(f"https://api.gbif.org/v1/species/{k}", retries=2)
            return d.get("canonicalName") or d.get("scientificName")
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=12) as ex:
        for nm in ex.map(resolve, missing):
            if nm:
                cn_names.add(nm.strip())
    json.dump(sorted(cn_names), open(out, "w"), ensure_ascii=False)
    print(f"[CN] Total resolved China fish species names: {len(cn_names)}")
    return cn_names


def default_view(order, family, genus):
    if order == "Pleuronectiformes":
        return "eyed-side"
    if order in DORSAL_ORDERS or family in DORSAL_FAMILIES:
        return "dorsal"
    if genus == "Hippocampus":
        return "vertical"
    return "lateral"


def safe_slug(s):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", s.strip())


# ---------- Stage 4: Assemble, Export & SQLite ----------
def build_all():
    col = fetch_col()
    wd = fetch_wikidata()
    cn_names = fetch_china_names(wd)

    col.sort(key=lambda x: (x["class"], x["order"], x["family"], x["scientificName"]))

    species_list = []
    by_order = defaultdict(list)
    stats = defaultdict(int)

    for seq, c in enumerate(col, 1):
        sci = c["scientificName"]
        sid = safe_slug(sci)
        w = wd.get(sci, {})
        ids = dict(w.get("ids", {}))
        ids["col"] = c["colId"]
        if w.get("wikidata"):
            ids["wikidata"] = w["wikidata"]
        if c["wormsFromCol"] and not ids.get("worms"):
            ids["worms"] = c["wormsFromCol"]

        names = dict(w.get("names", {}))
        zh = dict(w.get("zh", {}))
        view = default_view(c["order"], c["family"], c["genus"])
        in_china = sci in cn_names
        is_flagship = sci in FLAGSHIP_V1

        order_dir = safe_slug(c["order"])
        fam_dir = safe_slug(c["family"])
        sticker_file = f"stickers/{order_dir}/{fam_dir}/{sid}.webp"

        rec = {
            "id": sid,
            "scientificName": sci,
            "authority": c["authority"],
            "taxonomy": {
                "system": f"Catalogue of Life {COL_VERSION}",
                "seq": seq,
                "class": c["class"],
                "order": c["order"],
                "family": c["family"],
                "genus": c["genus"],
            },
            "names": names,
            "zh": zh,
            "ids": ids,
            "habitat": {
                "environments": c["environments"],
            },
            "extinctionStatus": "extinct" if c["extinct"] else None,
            "conservation": {"iucn": w.get("iucn")} if w.get("iucn") else {},
            "inChina": in_china,
            "sticker": {
                "file": sticker_file,
                "status": "pending",
                "kind": "ai-illustration",
                "view": view,
                "refTier": None,
                "colorConfidence": None,
                "reviewScore": None,
                "meetsQualityBar": False,
                "license": "CC-BY-4.0",
                "reference": None,
            },
            "taxonConcept": "same",
            "previous": [],
            "dataNotes": [],
        }
        species_list.append(rec)
        by_order[order_dir].append(rec)

        stats["total"] += 1
        if c["extinct"]: stats["extinct"] += 1
        if in_china: stats["in_china"] += 1
        if in_china or is_flagship: stats["v1_candidates"] += 1
        if names.get("zh-Hans"): stats["zh_hans"] += 1
        if names.get("zh-Hant"): stats["zh_hant"] += 1
        if names.get("en"): stats["en"] += 1
        if ids.get("fishbase"): stats["fishbase"] += 1
        if ids.get("worms"): stats["worms"] += 1
        if ids.get("gbif"): stats["gbif"] += 1
        if ids.get("wikidata"): stats["wikidata"] += 1
        if ids.get("inaturalist"): stats["inaturalist"] += 1
        if w.get("iucn"): stats["iucn"] += 1
        if c["environments"]: stats["environments"] += 1

    # 1. Export per-order JSONs (< 20 MB each)
    max_order_mb = 0.0
    order_index = []
    for order_dir, recs in sorted(by_order.items()):
        p = f"{DATA}/species/{order_dir}.json"
        payload = {
            "version": "0.1.0-skeleton",
            "taxonomy": f"Catalogue of Life {COL_VERSION}",
            "order": recs[0]["taxonomy"]["order"],
            "count": len(recs),
            "species": recs,
        }
        json.dump(payload, open(p, "w"), ensure_ascii=False, separators=(",", ":"))
        mb = os.path.getsize(p) / (1024 * 1024)
        max_order_mb = max(max_order_mb, mb)
        order_index.append({"order": recs[0]["taxonomy"]["order"], "file": f"data/species/{order_dir}.json",
                            "count": len(recs), "sizeMB": round(mb, 2)})
    json.dump({"version": "0.1.0-skeleton", "taxonomy": f"Catalogue of Life {COL_VERSION}",
               "totalSpecies": len(species_list), "orderCount": len(order_index), "orders": order_index},
              open(f"{DATA}/orders.json", "w"), ensure_ascii=False, indent=2)

    # 2. Export lightweight stickers.json
    stickers_idx = {
        "version": "0.1.0-skeleton",
        "cdn": "https://cdn.jsdelivr.net/gh/genhuipeng46-source/world-fish-sticker@main/",
        "credit": "Illustration: world-fish-sticker, CC BY 4.0",
        "count": len(species_list),
        "stickers": [
            {
                "id": r["id"],
                "scientificName": r["scientificName"],
                "en": r["names"].get("en", ""),
                "zh": r["names"].get("zh-Hans", ""),
                "file": r["sticker"]["file"],
                "status": r["sticker"]["status"],
            }
            for r in species_list
        ],
    }
    json.dump(stickers_idx, open(f"{DATA}/stickers.json", "w"), ensure_ascii=False, separators=(",", ":"))

    # 3. Export species.csv (UTF-8 BOM for Excel)
    with open(f"{DATA}/species.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            "id", "seq", "class", "order", "family", "scientific_name", "authority",
            "name_en", "name_zh_hans", "name_zh_hant", "environments", "extinction_status",
            "in_china", "col", "fishbase", "worms", "gbif", "wikidata", "inaturalist", "iucn",
            "sticker_file", "sticker_status", "sticker_view", "ref_tier", "color_confidence",
            "review_score", "meets_quality_bar",
        ])
        for r in species_list:
            w.writerow([
                r["id"], r["taxonomy"]["seq"], r["taxonomy"]["class"], r["taxonomy"]["order"],
                r["taxonomy"]["family"], r["scientificName"], r["authority"],
                r["names"].get("en", ""), r["names"].get("zh-Hans", ""), r["names"].get("zh-Hant", ""),
                "|".join(r["habitat"]["environments"]), r["extinctionStatus"] or "",
                r["inChina"], r["ids"].get("col", ""), r["ids"].get("fishbase", ""),
                r["ids"].get("worms", ""), r["ids"].get("gbif", ""), r["ids"].get("wikidata", ""),
                r["ids"].get("inaturalist", ""), r["conservation"].get("iucn", ""),
                r["sticker"]["file"], r["sticker"]["status"], r["sticker"]["view"],
                r["sticker"]["refTier"] or "", r["sticker"]["colorConfidence"] or "",
                r["sticker"]["reviewScore"] or "", r["sticker"]["meetsQualityBar"],
            ])

    # 4. Export names.csv & languages.json
    langs = ["en", "zh-Hans", "zh-Hant", "ja", "ko", "fr", "de", "es", "pt", "ru"]
    with open(f"{DATA}/names.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["id", "scientific_name"] + langs)
        for r in species_list:
            w.writerow([r["id"], r["scientificName"]] + [r["names"].get(l, "") for l in langs])
    json.dump([{"code": l, "source": "Wikidata (CC0)"} for l in langs],
              open(f"{DATA}/languages.json", "w"), ensure_ascii=False, indent=2)

    # 5. Export v1.0 launch candidate queue (China + flagship, non-extinct)
    v1 = [
        {"id": r["id"], "scientificName": r["scientificName"], "zh": r["names"].get("zh-Hans", ""),
         "en": r["names"].get("en", ""), "order": r["taxonomy"]["order"], "family": r["taxonomy"]["family"],
         "view": r["sticker"]["view"], "inaturalist": r["ids"].get("inaturalist"),
         "gbif": r["ids"].get("gbif"), "flagship": r["scientificName"] in FLAGSHIP_V1}
        for r in species_list
        if not r["extinctionStatus"] and (r["inChina"] or r["scientificName"] in FLAGSHIP_V1)
    ]
    json.dump({"version": "v1.0-candidates", "count": len(v1), "species": v1},
              open(f"{DATA}/v1_queue.json", "w"), ensure_ascii=False, indent=1)

    # 6. Initialize SQLite state DB
    dbp = f"{REPO}/pipeline/state.db"
    conn = sqlite3.connect(dbp)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS species (
            id TEXT PRIMARY KEY,
            scientific_name TEXT NOT NULL,
            class_name TEXT,
            order_name TEXT,
            family_name TEXT,
            zh_hans TEXT,
            en_name TEXT,
            view TEXT,
            in_china INTEGER,
            v1_target INTEGER,
            extinct INTEGER,
            inat_id INTEGER,
            gbif_id TEXT,
            ref_tier TEXT,
            color_confidence TEXT,
            status TEXT DEFAULT 'pending',
            rounds INTEGER DEFAULT 0,
            review_score INTEGER,
            meets_quality_bar INTEGER DEFAULT 0,
            last_corrections TEXT,
            cost_usd REAL DEFAULT 0.0,
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            species_id TEXT,
            round INTEGER,
            model TEXT,
            image_path TEXT,
            scores_json TEXT,
            passed INTEGER,
            corrections_json TEXT,
            cost_usd REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.executemany(
        """INSERT OR REPLACE INTO species
           (id, scientific_name, class_name, order_name, family_name, zh_hans, en_name, view,
            in_china, v1_target, extinct, inat_id, gbif_id)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        [
            (r["id"], r["scientificName"], r["taxonomy"]["class"], r["taxonomy"]["order"],
             r["taxonomy"]["family"], r["names"].get("zh-Hans", ""), r["names"].get("en", ""),
             r["sticker"]["view"], int(r["inChina"]),
             int(not r["extinctionStatus"] and (r["inChina"] or r["scientificName"] in FLAGSHIP_V1)),
             int(bool(r["extinctionStatus"])),
             r["ids"].get("inaturalist"), r["ids"].get("gbif"))
            for r in species_list
        ],
    )
    conn.commit()
    conn.close()

    # Print summary
    print("\n=== M1 SKELETON SUMMARY ===")
    for k, v in stats.items():
        pct = 100.0 * v / stats["total"] if stats["total"] else 0
        print(f"  {k:16s}: {v:6d} ({pct:5.1f}%)")
    print(f"  orders          : {len(order_index)} (largest file: {max_order_mb:.2f} MB)")
    print(f"  stickers.json   : {os.path.getsize(f'{DATA}/stickers.json')/1024/1024:.2f} MB")
    print(f"  species.csv     : {os.path.getsize(f'{DATA}/species.csv')/1024/1024:.2f} MB")
    print(f"  names.csv       : {os.path.getsize(f'{DATA}/names.csv')/1024/1024:.2f} MB")
    print(f"  v1_queue.json   : {len(v1)} species")
    print(f"  SQLite DB       : {dbp}")


if __name__ == "__main__":
    build_all()
