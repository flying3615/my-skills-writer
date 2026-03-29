---
name: daily-press-scanner
description: Use when extracting text from translated Chinese newspaper PDFs, then browsing and expanding articles in chat.
---

# Daily Press Scanner Skill

这个 skill 现在是轻量输入层，不再负责本地文章识别和本地摘要生成。

职责边界：

1. 本地脚本只负责下载 PDF、提取文字层、写页级文本和 `results.json`
2. 后续 AI 负责识别重点文章、排序、摘要和单篇展开

适用对象是**中文版机器翻译报纸 PDF**。目标是给聊天里的 AI 一个干净、稳定、低依赖的输入，而不是在本地规则里重建整份报纸。

## 主入口

唯一维护的入口是：

```bash
python3 daily-press-scanner/scripts/extract.py \
  --source-config daily-press-scanner/configs/sources.example.json \
  --out-dir ./out \
  --run-date 2026-03-29
```

也支持单个 URL：

```bash
python3 daily-press-scanner/scripts/extract.py \
  --url "https://dl.dengtazk.xin/%E3%80%90%E8%AF%91%E3%80%91%E7%BA%BD%E7%BA%A6%E6%97%B6%E6%8A%A5-3-29.pdf" \
  --out-dir ./out
```

也支持 URL 列表：

```bash
python3 daily-press-scanner/scripts/extract.py \
  --urls urls.txt \
  --out-dir ./out
```

`scan.py` 只保留兼容 wrapper，不应再作为主入口使用。

## 输入方式

推荐 `--source-config`，适合每日自动化。

示例：

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

支持占位符：

- `{year}`
- `{month}`
- `{day}`
- `{date}`

如果不传 `--run-date`，默认使用当天日期。

## 运行前提

必需：

- `python3`
- `pdftotext`
  通常来自 `poppler`，是首选文字层提取器。
- `pymupdf`
  当 `pdftotext` 不可用或失败时自动 fallback。

## 脚本行为

脚本只做这几件事：

1. 解析 `--url` / `--urls` / `--source-config`
2. 下载 PDF
3. 优先用 `pdftotext` 提取文字层
4. 失败时自动 fallback 到 `PyMuPDF`
5. 写出页级文本到 `text/<paper_slug>/page-XXX.txt`
6. 写出 `results.json`
7. 每份报纸处理结束后删除本地工作 PDF

脚本不做：

- 本地文章切分
- 本地重点排序
- 本地摘要生成
- 默认 OCR 主流程

## 输出目录

```text
out/
  results.json
  text/
    <paper_slug>/
      page-001.txt
      page-002.txt
      ...
```

`results.json` 是主 contract，至少包含：

- `run_date`
- `inputs`
- `papers`

每份 `paper` 至少包含：

- `source_name`
- `paper_id`
- `url`
- `source_record`
- `status`
- `method`
- `pages`
- `page_list`
- `text_dir`
- `error`

## 聊天使用方式

### Browse Mode

第一次回答优先返回“重点文章列表”，不要先铺开整篇长文。

每篇至少带：

- 编号
- 标题
- 页码
- 1-2 句简介

如果文章标题不完全清晰，可以用“主题 + 页码”的方式描述，但仍然要保持可选列表结构。

### Read Mode

当用户点名某篇文章后：

1. 返回该文的整理版正文、长摘要或结构化要点
2. 在回答尾部再次附上“简版文章列表”

这个尾部列表至少保留：

- 编号
- 标题
- 页码
- 极短简介

目的很简单：用户看完一篇后，不需要上翻很久就能继续选下一篇。

### Article Retrieval

AI 在浏览模式里先用 `text/<paper_slug>/page-*.txt` 自己识别和排序重点文章。

用户要求展开某篇时：

1. 根据编号找到对应标题和页码
2. 回到相关页文本
3. 提取并整理该篇正文
4. 返回正文整理结果
5. 尾部再附上简版文章列表

如果一页里有多篇内容，优先根据标题和上下文做页内定位，而不是把整页全文原样倾倒给用户。

## 上下文压缩策略

当聊天上下文接近上限时，必须按这个优先级压缩：

1. 优先保留重点文章列表
2. 优先保留每篇文章的短简介
3. 优先保留编号、页码、标题映射
4. 优先压缩已经展示过的单篇长文细节

换句话说，宁可把已展开文章压成 `5-8` 条要点，也不要丢掉文章列表。

## 推荐回答节奏

1. 先给本期报纸的重点文章列表
2. 用户点一篇，就展开那一篇
3. 展开后在末尾重贴简版列表
4. 用户继续点下一篇

这个 skill 适合“先浏览，再深挖”的阅读流，不适合一次性输出整份报纸全文。

## 错误处理

- 单份报纸失败不影响整批
- 下载失败或提取失败会写进 `results.json`
- 不管成功失败，工作 PDF 都应在处理结束后删除

## 非目标

- 英文原文对齐
- 跨页精确拼接
- 默认 OCR 主流程
- 在本地脚本里直接产出最终日报摘要
