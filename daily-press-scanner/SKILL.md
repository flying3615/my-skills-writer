---
name: daily-press-scanner
description: Use when processing translated Chinese newspaper PDF URLs into extracted text, article candidates, and summary artifacts for daily automation.
---

# Daily Press Scanner Skill

处理**中文版机器翻译报纸 PDF**，提取文字层并生成结构化摘要。

## 工作流程（两步走）

### 第一步：脚本提取（本地）

```bash
python3 daily-press-scanner/scripts/scan.py \
  --urls urls.txt \
  --out-dir ./out \
  --run-date 2026-03-28
```

或使用 source-config：

```bash
python3 daily-press-scanner/scripts/scan.py \
  --source-config daily-press-scanner/configs/sources.example.json \
  --out-dir ./out \
  --run-date 2026-03-28
```

脚本负责：
1. 下载 PDF（支持 URL 模板 + 日期展开）
2. 提取文字层（pdftotext 优先，PyMuPDF 自动 fallback）
3. 写出页级文本文件到 `text/<paper_slug>/page-001.txt` ...
4. 写出 `results.json`（含 paper 元信息、页索引、错误记录）

### 第二步：AI 分析（必须）

**脚本不负责文章识别和摘要——交给 AI。**

脚本跑完后，AI agent 应该：

1. 读取 `out/text/<paper_slug>/` 下所有 `page-*.txt` 文件
2. 从全部页面中识别文章标题和页码
3. 按重要性选出 **Top 10** 重点文章
4. 对每篇重点文章写出 **3-5 句中文摘要**
5. 列出其他值得关注的文章标题

AI 分析结果写入 `out/summary.md`，格式：

```markdown
# 《报纸名》中文翻译版 每日摘要

## 📰 报纸基本信息
- 日期、总页数、版面分布

## 🔥 Top 10 重点文章
### 1. 文章标题
**页码：** A1, A6
摘要内容...

## 📋 其他值得关注的文章
| 标题 | 页码 |
```

### 用户点阅某篇文章时

AI 回到 `text/<paper_slug>/page-XXX.txt` 读取该页完整文本，提取并呈现全文。

## 运行前提

**必需：**
- `python3`
- `pymupdf`（`pip install pymupdf`）— 文字层提取的主力

**可选（增强）：**
- `pdftotext`（来自 `poppler`）— 如果可用，脚本会优先使用；不可用时自动 fallback 到 PyMuPDF
- `pdftoppm` — OCR fallback，translated PDF 通常不需要

## 推荐输入方式

推荐用 `--source-config`，适合每日自动化：

```json
{
  "sources": [
    {
      "source_name": "Wall Street Journal",
      "url_template": "https://dl.dengtazk.xin/%E3%80%90%E8%AF%91%E3%80%91%E5%8D%8E%E5%B0%94%E8%A1%97%E6%97%A5%E6%8A%A5-{month}-{day}.pdf",
      "enabled": true
    }
  ]
}
```

占位符：`{year}` `{month}` `{day}` `{date}`

## 输出目录

```text
out/
  results.json      # 脚本主产物：paper 元信息、页索引、错误
  summary.md        # AI 生成的重点文章摘要（人类阅读）
  pdfs/             # 下载的原始 PDF
  text/             # 页级文字层文本
    <paper_slug>/
      page-001.txt
      page-002.txt
      ...
```

## 核心策略

### Text Layer First

- 优先 `pdftotext`（如果系统已安装）
- 自动 fallback 到 PyMuPDF（`pymupdf` Python 包）
- OCR 仅在文字层完全不可用时作为最后手段
- 对 translated PDF，文字层几乎总是可用的

### 脚本只做提取，AI 做分析

脚本不再尝试用本地规则做文章分块/打分/摘要（效果差，版头被误识别为文章）。

**职责划分：**
- **脚本**：下载 → 提取文字层 → 写页级文本 → 输出元数据
- **AI**：读页级文本 → 识别文章 → 打分排序 → 写摘要

### Browse First, Expand Later

1. AI 读完所有页面后生成 Top 10 摘要
2. 用户点名某篇 → AI 回到对应页面提取全文
3. 不需要重新下载 PDF 或重新处理

## 何时使用

- 用户给了一组中文版报纸 PDF 链接
- 用户想做每日自动化简报
- 用户希望快速了解报纸重点内容

## 错误处理

失败写进 `results.json` 的 `errors` 数组：
- 下载失败（SSL 问题等，脚本已内置 SSL fallback）
- 文字层不可用
- 页级处理失败

单份报纸失败不影响整批。
