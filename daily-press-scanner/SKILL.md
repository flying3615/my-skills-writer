---
name: daily-press-scanner
description: Use when scanning batches of newspaper PDF URLs to find opinion pieces, commentary, or topic-specific stories from OCR-only pages and return structured JSON.
---

# Daily Press Scanner Skill

这个 Skill 用于处理一组**当日报纸 PDF URL**，在大多数页面没有文字层、只能依赖 OCR 的前提下，快速找出：

- 评论员文章
- 社论、分析、专栏、书评
- 用户指定热门主题对应的新闻页或文章

默认目标不是还原整份报纸，而是先输出**结构化 JSON 索引**，方便后续人工筛选、深度摘要、脚本改写或别的工作流消费。

## 可执行脚本

这个 Skill 自带一个纯本地扫描脚本：

```bash
python3 daily-press-scanner/scripts/scan.py \
  --urls urls.txt \
  --out-dir ./out \
  --topics tariffs,ai,china,fed,war,markets \
  --max-pages 12 \
  --dpi 200
```

### 运行前提

- `python3`
- `pdftoppm`
- `tesseract`
- 可选：`pypdf`、`Pillow`

### 输入文件格式

`--urls` 指向一个文本文件，每行一条 PDF URL 或本地路径。支持：

- `https://.../paper.pdf`
- `file:///.../paper.pdf`
- `/absolute/path/to/paper.pdf`

空行和以 `#` 开头的行会被忽略。

`--topics` 的语义是：

- 不传：使用脚本内置默认主题集
- 传入：只扫描你指定的主题，不再附带默认全集

### 输出目录

脚本会在 `--out-dir` 下写出：

```text
out/
  results.json
  pdfs/
  ocr/
  previews/
```

- `results.json` 是主输出，供后续助手消费。
- `pdfs/` 保存下载后的 PDF。
- `ocr/` 保存逐页 OCR 原文。
- `previews/` 保存逐页渲染图和摘要文本。

### 消费原则

当脚本已经生成 `results.json` 时，助手应优先读取 JSON，而不是再次对 PDF 做重复 OCR。
这个脚本本身不调用远程 AI，也不做中文摘要生成；这些解释和筛选动作应由使用该 skill 的助手基于 `results.json` 完成。

## 何时使用

适合这些场景：

- 用户一次给了多份报纸 PDF URL
- PDF 大多是扫描件，没有文字层
- 用户更关心 `Opinion / Editorial / Analysis / Column / Review`
- 用户想快速找特定主题，例如关税、AI、中东、中国、Fed、市场
- 用户需要 JSON 结果，而不是终端长篇摘要

不适合这些场景：

- 需要完整还原整份报纸全文
- 需要精确拼接所有跨页续写文章
- 需要直接生成视频成品

## 核心策略

不要默认对所有页面做最重的 `OCR + AI 清洗 + 分篇`。

采用两层处理：

1. `fast_scan`
   - 对每页做轻量 OCR
   - 只抓标题感文本、首段、数字、人名、国家、公司名
   - 用于页级主题判断和评论页候选识别

2. `selective_review`
   - 只对命中的少量页面做进一步人工或助手层解读
   - 脚本负责准备 OCR 原文和索引，不在脚本里接远程 AI

默认不纠结首页文章跳转到后页的续写问题。首页热门新闻通常不是主要目标；优先把资源放在评论页和特定热点上。

## 输入

输入应是一组 PDF URL，例如：

```text
https://example.com/financial-times-3-25.pdf
https://example.com/new-york-times-3-25.pdf
https://example.com/wall-street-journal-3-25.pdf
```

可附带：

- 关注主题列表，例如：`tariffs, ai, china, fed, war, markets`
- 需要优先查找的栏目，例如：`opinion, editorial, analysis, review`
- 每份报纸最多快扫多少页

推荐执行方式：

```bash
python3 daily-press-scanner/scripts/scan.py \
  --urls urls.txt \
  --out-dir ./out \
  --topics tariffs,ai \
  --max-pages 8
```

## 输出

输出应是单个 `results.json`，而不是自然语言大段描述。

建议结构：

```json
{
  "run_date": "2026-03-26",
  "inputs": [
    "https://example.com/financial-times-3-25.pdf"
  ],
  "papers": [
    {
      "source_name": "Financial Times",
      "url": "https://example.com/financial-times-3-25.pdf",
      "page_count": 24,
      "status": "ok"
    }
  ],
  "page_index": [
    {
      "source_name": "Financial Times",
      "page": 3,
      "title": "Brittin will need luck as well as talent to steer embattled BBC",
      "snippet": "..."
    }
  ],
  "opinion_candidates": [
    {
      "source_name": "Financial Times",
      "page": 3,
      "title": "Brittin will need luck as well as talent to steer embattled BBC",
      "section_guess": "Analysis",
      "snippet": "Former Google executive faces tough policy and political challenges...",
      "topic_tags": [],
      "confidence": 0.82
    }
  ],
  "topic_hits": [
    {
      "source_name": "Financial Times",
      "page": 2,
      "topic": "inflation",
      "title": "Inflation fallout",
      "snippet": "Businesses call for energy policy changes...",
      "score": 0.78
    }
  ],
  "errors": []
}
```

## 操作流程

### 1. 下载 PDF

- 下载所有 URL
- 记录下载失败到 `errors`
- 不因单份报纸失败而中断整批任务

### 2. 页级 OCR 快扫

对每份报纸逐页处理，但默认限制在一个合理页数范围内，例如前 `8-12` 页。第一版脚本不会自动补扫后续评论区页面；如果需要扩大范围，请显式调高 `--max-pages`。

快扫时：

- 优先识别页面主标题
- 抽取首段前几行
- 记录明显数字、人物、公司、国家
- 给出粗粒度主题标签

### 3. 评论页识别

优先找这些信号：

- 页眉或栏目中出现：
  - `Opinion`
  - `Editorial`
  - `Analysis`
  - `Column`
  - `Review`
  - `Books`
  - `Comment`
- 标题风格明显像专栏或评论
- 作者行 `By ...` 比较清晰

### 4. 热点主题匹配

根据用户给定主题做匹配，不要求全文精读。

主题匹配可基于：

- 标题命中
- 首段命中
- 命名实体命中
- 数字和关键短语

例如：

- `tariffs`: tariff, trade, duty, import, export
- `fed`: inflation, rates, Powell, Federal Reserve
- `china`: Beijing, China, Xi, property, yuan
- `war`: missile, strike, Gaza, Ukraine, Iran, Israel
- `ai`: artificial intelligence, chip, Nvidia, OpenAI, model

### 5. 命中页复查

仅对这些页面进入复查：

- 评论候选页
- 高分 topic hit 页

复查目标：

- 标题
- 栏目
- OCR 原文是否可读
- 主题标签

如果页面过于脏乱，允许只保留：

- `title`
- `page`
- `snippet`
- `matched_terms`

不要为了追求完美而卡死整批流程。

## 处理规则

- OCR-only 页面也先做快扫，不要默认重型清洗
- 首页续写问题默认弱化处理，不作为第一版主目标
- 评论候选优先级高于普通新闻页
- 热点新闻只要足够判断主题即可，不要求完整还原全文
- 输出要结构化、可复用、可缓存

## 错误处理

必须把失败写进 `errors`：

- 下载失败
- OCR 失败
- 页内容过脏无法判断

错误只影响当前 PDF 或当前页，不影响整个批次。

## 示例提示词

- `扫描这 4 份报纸 PDF URL，优先找 opinion 和 analysis，输出 JSON。`
- `从这些日报里找跟 tariffs、China、AI 相关的话题页，返回结构化结果。`
- `只提取评论员文章，不要跑完整报纸全文清洗。`

## 非目标

第一版默认不做：

- 全报纸逐篇全文还原
- 完整跨页文章拼接
- 视频脚本生成
- 上传或内容生产
- GUI 或网页展示
