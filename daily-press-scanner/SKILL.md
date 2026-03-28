---
name: daily-press-scanner
description: Use when processing translated Chinese newspaper PDF URLs into extracted text, article candidates, and summary artifacts for daily automation.
---

# Daily Press Scanner Skill

这个 Skill 现在的主目标已经不是“对英文扫描报纸做 OCR 快扫”，而是处理一组**中文版机器翻译报纸 PDF**，优先利用 PDF 自带的中文文字层，生成：

- 可复用的页级文本产物
- 结构化 `article_candidates`
- 每份报纸 `5-10` 篇重点条目的本地 summary contract

它适合给后续 Codex 自动化当作每日输入准备层，不要求完美还原原版文章，也不默认追求跨页拼接。

## 当前实现重点

当前脚本已经支持这条主路径：

1. 固定 URL 模板 + 日期展开
2. 下载中文版 PDF
3. 检测并提取文字层
4. 写出页级 text artifacts
5. 从页级中文文本生成 `article_candidates`
6. 本地规则筛出每份报纸的重点条目
7. 写出 `summary.json` / `summary.md`

旧的 OCR 扫描能力仍然存在，但对 translated PDF 来说已经不是默认优化方向。

## 可执行脚本

```bash
python3 daily-press-scanner/scripts/scan.py \
  --source-config translated-press-scanner/configs/sources.example.json \
  --out-dir ./out \
  --run-date 2026-03-27
```

也仍然兼容旧的 `--urls` 输入：

```bash
python3 daily-press-scanner/scripts/scan.py \
  --urls urls.txt \
  --out-dir ./out
```

## 运行前提

- `python3`
- `pdftotext`
- 旧 OCR 路径相关依赖在需要时仍会用到：
  - `pdftoppm`
  - `tesseract`
- 可选：
  - `pypdf`
  - `Pillow`

## 推荐输入方式

推荐用 `--source-config`，因为这更适合每日自动化。

示例配置：

```json
{
  "sources": [
    {
      "source_name": "New York Times",
      "url_template": "https://dl.dengtazk.xin/%E3%80%90%E8%AF%91%E3%80%91%E7%BA%BD%E7%BA%A6%E6%97%B6%E6%8A%A5-{month}-{day}.pdf",
      "enabled": true
    }
  ]
}
```

支持的占位符：

- `{month}`
- `{day}`
- `{year}`
- `{date}`

如果不传 `--run-date`，默认使用当天日期。

## 输出目录

脚本会在 `--out-dir` 下写出：

```text
out/
  results.json
  articles.json
  summary.json
  summary.md
  daily_brief.json
  pdfs/
  text/
  ocr/
  previews/
```

重点产物说明：

- `results.json`
  - 主运行产物，包含 papers、page_index、errors、article candidates、summary contract
- `articles.json`
  - 给后续 AI 或自动化消费的完整文章库，是按需展开正文的主数据源
- `summary.json`
  - 每份报纸的重点条目摘要 contract
- `summary.md`
  - 人类直接阅读版
- `daily_brief.json`
  - 给每日 Codex 自动化消费的扁平摘要 payload
- `text/`
  - 成功提取的页级文字层文本，路径类似 `text/<paper_slug>/page-001.txt`

## 核心策略

### 1. Text Layer First

对 translated PDF，优先跑 `pdftotext`。

- 如果文字层可用，写出页级 `text_path`
- 如果文字层是明显的中文译文内容，直接走 text-layer fast path，不再跑整页 render/OCR/review
- 如果文字层不可用，记录 `text_layer_status` / `text_layer_reason`
- OCR 只作为文字层不可用时的 fallback

### 2. Article Candidates Before Summary

不要直接拿整份 PDF 做总结。

先从每页中文文本生成 `article_candidates`，每条至少包含：

- `article_id`
- `source_name`
- `paper_id`
- `url`
- `page`
- `title`
- `title_guess`
- `title_normalized`
- `byline`
- `body_text`
- `section_guess`
- `topic_tags`
- `importance_hints`
- `priority_score`
- `lookup_keys`
- `text_path`

当前实现不是跨页文章重建，但也不再是“整页一条”的粗粒度模式：

- 前 `10` 页会优先使用 `pdftotext -bbox-layout` 的 block 坐标做 article-like block extraction
- 如果 bbox 提取不可用，才退回 text-line 分块
- 第 `11-30` 页仍保留页级 fallback
- 如果前页分块失败，会自动退回页级 candidate

### 3. Browse First, Expand Later

脚本当前不会调用远程 AI API。

它会先用本地规则对 `article_candidates` 做排序和裁剪，保证每份报纸最终输出 `5-10` 条重点项，并写出：

- `summary.json`
- `summary.md`
- `daily_brief.json`

推荐的使用方式是：

1. 先让 AI 读 `daily_brief.json`，返回重点文章摘要列表
2. 用户点名某篇文章后，再让 AI 用 `article_id` 或 `page + title` 去 `articles.json` 回取完整正文

这样后续 Codex 自动化或安装这个 skill 的 AI，不需要重新下载 PDF，也不需要自己做文章匹配。

## 何时使用

适合这些场景：

- 用户给了一组中文版报纸 PDF 链接
- 用户想做每日自动化
- 用户更关心“给 AI 一个干净输入”，而不是逐字忠实还原英文原版
- 用户希望每份报纸得到 `5-10` 篇重点内容

不适合这些场景：

- 需要原文级校对
- 需要完整跨页拼接文章
- 需要生成最终发布稿件
- 需要依赖 OCR 还原没有文字层的原始英文扫描件作为主流程

## 当前处理流程

### 1. Source Resolution

- 读取 `--source-config` 或 `--urls`
- 如果是 config，按日期展开 URL 模板
- 保留 `source_name` 和原始 source metadata

### 2. Download

- 下载 PDF 到 `pdfs/`
- 失败写入 `errors`
- 单份报纸失败不影响整批

### 3. Text Layer Extraction

- 使用 `pdftotext`
- 评估文字层是否可用
- 成功时把每页文本写入 `text/`
- 对中文译文文字层，直接从页级文本构建 `page_index`

### 4. Candidate Generation

- 从 `text_path` 读取页级文本
- 去掉明显版头、日期、天气、价格、服务指南、音频/视频导流等 page furniture
- 前 `10` 页优先按 bbox blocks 聚合标题、作者和正文块
- bbox 不可用时，再按标题行、作者行、正文密度做 text-line 分块
- 生成更接近文章粒度的 `article_candidates`

### 5. Local Summary Contract

- 对 candidates 打分
- 每份报纸裁到最多 `10` 条
- 写出 `summary.json`、`summary.md` 和 `daily_brief.json`

## 主要字段

### `paper`

每份报纸的摘要元信息包含：

- `source_name`
- `paper_id`
- `url`
- `status`
- `text_layer_status`
- `text_layer_reason`
- `text_layer_score`
- `text_layer_dir`
- `text_layer_page_count`
- `article_count`
- `scan_mode`

### `page_index`

页级索引仍然保留，尤其是为了兼容旧扫描流程。对 translated 路径，重点字段是：

- `page`
- `text_path`
- `preview_path`
- `ocr_path`

### `article_candidates`

这是后续自动化最应该优先消费的中间层。

当前会额外带一些结构字段，便于本地排序：

- `article_id`
- `title`
- `title_normalized`
- `byline`
- `block_index`
- `block_kind`
- `source_page_rank`
- `priority_score`
- `lookup_keys`

### `summary.json`

每份报纸大致形如：

```json
{
  "run_date": "2026-03-27",
  "papers": [
    {
      "source_name": "New York Times",
      "paper_id": "nyt-2026-03-27",
      "article_count": 14,
      "selected_count": 8,
      "selected_articles": [
        {
          "page": 1,
          "title_guess": "战争冲击波引发滞胀阴影",
          "summary_text": "..."
        }
      ]
    }
  ],
  "articles": []
}
```

### `daily_brief.json`

这个文件是为了自动化消费而加的更扁平版本。每份报纸只保留：

- `source_name`
- `paper_id`
- `selected_count`
- `articles`

每篇文章最少包含：

- `article_id`
- `page`
- `title`
- `byline`
- `priority_score`
- `summary_text`
- `topic_tags`
- `text_path`

## 消费原则

- 对 translated PDF，优先看 `daily_brief.json` 和 `articles.json`
- 不要优先回退到 OCR 文本
- 如果 `text_layer_status` 是 `available`，优先使用 `text_path`
- 如果要接真正的 AI：
  - 第一步读 `daily_brief.json` 做摘要浏览
  - 第二步按 `article_id` 或 `page + title` 去 `articles.json` 拿完整 `body_text`

## 错误处理

失败必须写进 `errors`：

- 下载失败
- `pdftotext` 不可用
- 文字层为空
- 文字层过稀疏
- 页级处理失败

错误按 paper 或 page 隔离，不影响整批运行。

## 非目标

当前版本默认不做：

- 自动跨页拼接
- 精确文章版面重建
- 远程 AI 直接集成进脚本
- 英文原文对齐
- 以 OCR 为主的 translated PDF 流程
