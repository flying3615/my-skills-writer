# My Skills Writer

这个仓库用于集中维护一组可复用的自定义 AI Skills。每个 skill 都围绕一个明确任务，通常附带 `SKILL.md` 指令文件，以及必要时的本地脚本，方便在聊天会话或自动化任务里直接调用。

## 当前包含的 Skills

### 1. [Daily Press Scanner](./daily-press-scanner/SKILL.md)
处理中文版机器翻译报纸 PDF 的轻量提取工具。
- 目标：把 PDF 转成适合后续 AI 阅读的页级文本输入。
- 主流程：优先 `pdftotext` 提取文字层，失败时回退到 `PyMuPDF`。
- 输出：`results.json` 和 `text/<paper_slug>/page-XXX.txt`。
- 入口脚本：`python3 daily-press-scanner/scripts/extract.py`
- 适合场景：先让 AI 生成重点文章列表，再按需展开单篇正文。

### 2. [News Summarizer](./news-summarizer/SKILL.md)
面向日常新闻浏览的聚合与摘要 skill。
- 目标：汇总新西兰、本地、国际和市场新闻，或按指定主题定向搜索。
- 输出：中文摘要 + 原文链接。
- 适合场景：每日新闻速览、临时热点追踪、主题化新闻搜索。

### 3. [NotebookLM Exporter](./notebooklm-exporter/SKILL.md)
NotebookLM CLI 的稳定工作流封装。
- 目标：管理 notebook、sources、artifacts，以及生成和下载导出内容。
- 常见能力：检查环境、列 notebook/source、添加 source、生成 video/report/quiz 等 artifact、导出下载。
- 依赖：`notebooklm-py`、Playwright Chromium、NotebookLM 登录态。
- 入口脚本：`notebook_ops.sh`、`source_ops.sh`、`artifact_ops.sh`、`generate_and_download.sh`

### 4. [Stock Value Scanner](./stock-value-scanner/SKILL.md)
面向美股的价值分析、趋势查看和市场异动扫描工具。
- 价值分析：估值指标、ROE、净利率、综合评分。
- 趋势分析：历史高点回撤、52 周区间、长期均线。
- 市场异动：涨幅榜、跌幅榜、热门交易股。
- 依赖：Python 库 `yfinance`
- 入口脚本：
  - `python3 stock-value-scanner/scripts/scanner.py`
  - `python3 stock-value-scanner/scripts/stock_price.py`
  - `python3 stock-value-scanner/scripts/market_movers.py`

### 5. [Video Downloader](./video-downloader/SKILL.md)
基于 `N_m3u8DL-RE` 的视频下载 skill。
- 目标：从用户给定链接下载视频，并按指定名称保存。
- 依赖：`nre` / `N_m3u8DL-RE`
- 入口脚本：`bash video-downloader/scripts/download.sh`

### 6. [Reading Vault Builder](./reading-vault-builder/SKILL.md)
面向书籍阅读理解的读书笔记库 skill。
- 目标：把书籍资料整理成 Obsidian 风格的 `ReadingVault/`
- 主输入：`PDF`、`epub`
- 次输入：`txt`、`md`、`url`
- 默认输出：中文章节笔记、主题索引、概念卡、引文页和轻量理解检查
- `epub` 提取脚本：`python3 reading-vault-builder/scripts/extract_epub.py --epub ./book.epub --out-dir ./out/epub-text`
- 适合场景：整理整本书、建立长期复习型笔记库、按章节阅读后再做跨章节回顾

## 仓库结构

```text
.
├── README.md
├── daily-press-scanner/
│   ├── SKILL.md
│   ├── configs/
│   │   └── sources.example.json
│   ├── scripts/
│   │   ├── extract.py
│   │   └── scan.py
│   └── tests/
├── news-summarizer/
│   └── SKILL.md
├── reading-vault-builder/
│   ├── SKILL.md
│   ├── references/
│   ├── scripts/
│   └── tests/
├── notebooklm-exporter/
│   ├── SKILL.md
│   ├── agents/
│   └── scripts/
├── stock-value-scanner/
│   ├── SKILL.md
│   └── scripts/
├── video-downloader/
│   ├── SKILL.md
│   └── scripts/
├── docs/
│   └── plans/
├── notebooklm_downloads/
└── translated-press-scanner/
```

## 使用建议

- 需要稳定的本地数据准备层：优先看 [Daily Press Scanner](./daily-press-scanner/SKILL.md)
- 需要快速新闻摘要：优先看 [News Summarizer](./news-summarizer/SKILL.md)
- 需要整理书籍并生成 Obsidian 读书笔记库：优先看 [Reading Vault Builder](./reading-vault-builder/SKILL.md)
- 需要操作 NotebookLM：优先看 [NotebookLM Exporter](./notebooklm-exporter/SKILL.md)
- 需要股票分析：优先看 [Stock Value Scanner](./stock-value-scanner/SKILL.md)
- 需要下载媒体内容：优先看 [Video Downloader](./video-downloader/SKILL.md)

## 维护原则

- 每个 skill 的真实行为以对应目录下的 `SKILL.md` 为准。
- 如果某个 skill 附带本地脚本，README 只描述主能力和入口，不重复全部实现细节。
- 当脚本入口、依赖或输出 contract 变化时，优先同步对应的 `SKILL.md`，再回写根目录 `README.md`。
