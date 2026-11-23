# world-fish-sticker：全球鱼类贴纸库与开放数据集

[English](README.md) · **简体中文**

> **当前状态：`0.1.0-skeleton`（M1 数据骨架已完成）**
> 已完成全量 **38,184 种**现生鱼类（93 目）的开放授权数据骨架、v1.0 首发队列（4,221 种）与 23 种试画校准。下一步进入 M2 批量生成流水线与 M3 v1.0 贴纸生产。详见 [需求文档](docs/需求文档.md) 与 [试画报告](docs/试画报告.md)。

按 [Catalogue of Life（2026-11-11）](https://www.catalogueoflife.org/) 整理的全球现生鱼类贴纸库与开放结构化数据集，覆盖盲鳗、七鳃鳗、软骨鱼、辐鳍鱼、肺鱼与腔棘鱼，共 38,184 个接受种、93 个目。项目结构、质量闭环与元数据规范受 [huashu-bird-sticker](https://github.com/alchaincyf/huashu-bird-sticker) 启发。

**AI 生成声明：** 所有贴纸均为 AI 绘制的写实插画，**不是照片，也不是专家核对过的分类图版**。每个贴纸文件的 XMP 元数据均写入 `IPTC DigitalSourceType = trainedAlgorithmicMedia`、AI 系统名称、授权与仓库链接。请勿将贴纸当作真实观察照片上传至 iNaturalist 等公民科学平台，也不要用于严肃物种鉴定。

**授权一句话：** 贴纸按 [CC BY 4.0](LICENSE.md) 授权，可免费用于任何用途（含商用），注明来源 `world-fish-sticker` 并附仓库链接即可；数据整理与代码按 [MIT](LICENSE.md) 授权；第三方字段来源与条款见 [NOTICE.md](NOTICE.md)。

## 里面有什么

| 路径 | 说明 |
|---|---|
| `stickers/<目>/<科>/<属_种>.webp` | 透明底白边贴纸，长边约 1000px，平均约 46 KB（M3 批量生产中） |
| `data/species/<目>.json` | 完整结构化数据，按 93 个目拆分（单文件均 < 5 MB，可直接走 jsDelivr） |
| `data/species.csv` | 全量 38,184 种摊平表格（UTF-8 BOM，Excel 直接打开不乱码，10.16 MB） |
| `data/stickers.json` | 网页/App 轻量索引（6.94 MB） |
| `data/names.csv` | 10 种语言鱼名表（Wikidata CC0，2.77 MB） |
| `data/v1_queue.json` | v1.0 首发候选队列（中国鱼类 + 经典观赏/经济鱼类，共 4,221 种） |
| `pipeline/` | 数据抓取、选图、生成、审核、抠图与导出流水线 |

详细字段与覆盖率统计见 [data/README.md](data/README.md)。

## 项目文档

- [需求文档.md](docs/需求文档.md)（v1.0 定稿）
- [调研报告.md](docs/调研报告.md)（物种数、授权、参考图抽样与 CDN 实测）
- [试画报告.md](docs/试画报告.md)（23 种闭环实测与 6 项规范修正）
- [项目说明文档.md](docs/项目说明文档.md)（技术架构与规范草案）

## 参与纠错与撤图

- 发现画错：[报告贴纸错误](.github/ISSUE_TEMPLATE/sticker-error.yml)
- 鱼名纠错：[报告鱼名错误](.github/ISSUE_TEMPLATE/name-error.yml)
- 熟悉某一科鱼类：[帮忙审一个科](.github/ISSUE_TEMPLATE/family-review.yml)
- 参考照片作者撤图：[提交撤图申请](.github/ISSUE_TEMPLATE/takedown.yml)（7 天内替换）
