# Data

All species data are aligned to **Catalogue of Life (2026-11-11, CC BY 4.0)** across all 7 extant fish groups (**38,184 accepted species**, 93 orders).

To stay below jsDelivr's 20 MB per-file limit and GitHub's 100 MB hard file limit, the full structured dataset is split by order under `data/species/<Order>.json` (largest file: **4.35 MB**).

| File | Contents | Size | License |
|---|---|---:|---|
| `orders.json` | Index of all 93 orders and their per-order JSON files | ~12 KB | MIT |
| `species/<Order>.json` | Full structured records for every species in that order | ≤ 4.35 MB each | MIT (compilation); third-party fields see [NOTICE.md](../NOTICE.md) |
| `species.csv` | Flattened spreadsheet table (UTF-8 BOM for Excel) | 10.16 MB | as above |
| `stickers.json` | Lightweight app/web index (`id`, `scientificName`, `en`, `zh`, `file`, `status`, CDN prefix) | 6.94 MB | MIT |
| `names.csv` | Common names in 10 languages (`en`, `zh-Hans`, `zh-Hant`, `ja`, `ko`, `fr`, `de`, `es`, `pt`, `ru`) | 2.77 MB | Wikidata (CC0) |
| `languages.json` | Language codes and sources | < 1 KB | MIT |
| `v1_queue.json` | v1.0 launch shortlist (China + flagship aquarium/economic species, non-extinct: **4,221 species**) | ~1.2 MB | MIT |

## Coverage (38,184 accepted species)

| Field | Covered | Share | Source |
|---|---:|---:|---|
| Taxonomy (`class`, `order`, `family`, `genus`, `authority`) | 38,184 | 100.0% | Catalogue of Life 2026-11-11 (CC BY 4.0) |
| COL ID & WoRMS AphiaID | 38,184 | 100.0% | Catalogue of Life / Wikidata |
| Environments (`freshwater` / `marine` / `brackish`) | 38,104 | 99.8% | Catalogue of Life |
| FishBase SpecCode & Wikidata QID | 33,825 | 88.6% | Wikidata (CC0) |
| GBIF taxonKey | 33,755 | 88.4% | Wikidata (CC0) |
| iNaturalist taxon ID | 32,456 | 85.0% | Wikidata (CC0) |
| Simplified Chinese name (`zh-Hans`) | 26,832 | 70.3% | Wikidata (CC0) |
| IUCN Red List category | 22,510 | 59.0% | Wikidata P141 (CC0) |
| Traditional Chinese name (`zh-Hant`) | 9,177 | 24.0% | Wikidata (CC0) |
| English common name (`en`) | 8,709 | 22.8% | Wikidata P1843 (CC0) |
| Extinct flag (`extinctionStatus: "extinct"`) | 289 | 0.8% | Catalogue of Life |
| China occurrence flag (`inChina: true`) | 4,213 | 11.0% | GBIF `country=CN` |

### v1.0 Launch Queue (`v1_queue.json`, 4,221 species)
- Simplified Chinese name: **3,778 (89.5%)**
- iNaturalist taxon ID: **4,025 (95.4%)**
- View routing: `lateral` 3,967 · `eyed-side` 128 · `dorsal` 111 · `vertical` 15

## Sticker Fields & Reference Tiers

Each species record includes a `sticker` object:
- `view`: `lateral` | `dorsal` | `eyed-side` | `vertical`
- `refTier`: `A` (open-licensed live photo) | `B` (NC/ND live photo, not redistributed) | `C` (preserved specimen / line art) | `D` (text description only)
- `colorConfidence`: `high` (tiers A/B) | `low` (tiers C/D)
- `reviewScore`, `meetsQualityBar`, `license` (`CC-BY-4.0`), `reference` (page, author, license — photos themselves are never stored in this repository)
