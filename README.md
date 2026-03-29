# My Skills Writer

这是一个用于存放和管理自定义 AI Skill 的项目。通过这些 Skill，可以增强 AI 助手的自动化能力，例如规范化 Skill 编写流程或自动化下载任务。

## 已包含的 Skill

### 1. [Skill Writer](./skill-writer/SKILL.md)
专门用于辅助创建、更新和优化 AI Skill 的工具。它定义了本项目中 Skill 的标准目录结构和编写规范。

### 2. [Video Downloader](./video-downloader/SKILL.md)
自动化视频下载工具，基于 `nre` (N_m3u8DL-RE) 命令。
- **功能**: 自动从用户提供的链接中提取视频并以指定名称保存。
- **依赖**: 需要安装 [N_m3u8DL-RE](https://github.com/nilaoda/N_m3u8DL-RE)。

### 3. [News Summarizer](./news-summarizer/SKILL.md)
每日新闻聚合与翻译工具。
- **功能**: 自动采集新西兰、国际及市场新闻，并支持针对用户指定主题执行深度搜索，提供中文摘要与链接。

### 4. [Stock Value Scanner](./stock-value-scanner/SKILL.md)
股票价值投资分析与实时股价查询工具。
- **功能**: 
  - **价值分析**: 基于 Yahoo Finance (yfinance) 分析股票估值（P/B, P/E, ROE）。
  - **趋势分析**: 分析历史高点回撤、52周幅度及长期均线趋势。
  - **市场异动**: 实时查看美股涨幅榜、跌幅榜及热门交易股。

### 5. [Daily Press Scanner](./daily-press-scanner/SKILL.md)
扫描多份当日报纸 PDF URL 的 OCR 索引工具，附带本地可执行扫描脚本。
- **功能**:
  - **快扫索引**: 对扫描报纸做页级 OCR 快扫，快速识别标题、首段和主题。
  - **评论优先**: 优先找 `Opinion / Editorial / Analysis / Column / Review` 候选文章。
  - **主题命中**: 按用户关心的话题输出结构化 JSON，如关税、AI、中国、Fed、中东等。
- **运行要求**: 需要 `python3`、`pdftoppm`、`tesseract`，可选 `pypdf` 和 `Pillow`。
- **执行方式**:
   ```bash
   python3 daily-press-scanner/scripts/scan.py --urls urls.txt --out-dir ./out --topics tariffs,ai --max-pages 8
   ```
- **主题参数**: 不传 `--topics` 时使用默认主题集；传入后只扫描指定主题。

### 6. [Macro Market Report](./macro-market-report/SKILL.md)
跨资产宏观市场报表工具。
- **功能**:
  - **一键快报**: 生成覆盖商品、股指、波动率、美元、美债和加密资产的中文市场报表。
  - **关键变化**: 输出最新价格与 `1日 / 5日 / 1个月` 涨跌幅。
  - **可扩展监控**: 支持通过 `--extra` 追加额外 ticker。
- **运行要求**: 需要 `python3` 和 `yfinance`。
- **执行方式**:
   ```bash
   python3 macro-market-report/scripts/market_report.py
   ```

## 目录结构

```text
.
├── README.md
├── skill-writer/        # Skill 编写规范
│   └── SKILL.md
├── video-downloader/    # 视频下载工具
│   ├── SKILL.md
│   └── scripts/
│       └── download.sh
├── news-summarizer/     # 新闻摘要工具
│   └── SKILL.md
├── stock-value-scanner/ # 股票价值分析工具
│   ├── SKILL.md
│   └── scripts/
│       ├── scanner.py
│       ├── stock_price.py
│       └── market_movers.py
├── daily-press-scanner/ # 报纸 OCR 快扫与评论/热点索引工具
│   ├── SKILL.md
│   └── scripts/
│       └── scan.py
└── macro-market-report/ # 跨资产宏观市场报表工具
    ├── SKILL.md
    ├── scripts/
    │   └── market_report.py
    └── tests/
        └── test_market_report.py
```

## 如何贡献

如果你想添加新的 Skill，请参考 `skill-writer` 中的规范进行创建，并将其放置在独立的文件夹中。
