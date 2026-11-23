# Changelog / 更新记录

## 0.1.0-skeleton — 2026-11-19

**M1 Data Skeleton built.** / **完成 M1 全球鱼类数据骨架。**

- Pulled all accepted extant fish species from Catalogue of Life (2026-11-11, CC BY 4.0) across Actinopterygii, Elasmobranchii, Holocephali, Myxini, Petromyzonti, Dipnoi, and Actinistia. / 从 Catalogue of Life（2026-11-11，CC BY 4.0）拉取全量现生鱼类接受种。
- Enriched with Wikidata (CC0) multilingual names, external IDs (FishBase, WoRMS, GBIF, iNaturalist), and IUCN status. / 接入 Wikidata（CC0）多语种名、外部编号与 IUCN 等级。
- Exported per-order JSONs (`data/species/<Order>.json`, each < 20 MB for GitHub/jsDelivr compatibility), `data/species.csv`, `data/stickers.json`, `data/names.csv`, and `data/v1_queue.json`. / 导出按目拆分的 JSON、摊平 CSV、轻量索引及 v1.0 首发队列。
- Completed M0.5 pilot across 23 species; see `docs/试画报告.md`. / 完成 23 种试画校准，详见 `docs/试画报告.md`。
