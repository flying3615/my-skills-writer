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
└── news-summarizer/     # 新闻摘要工具
    └── SKILL.md
└── stock-value-scanner/ # 股票价值分析工具
    ├── SKILL.md
    └── scripts/
        ├── scanner.py
        ├── scanner.py
        ├── stock_price.py
        └── market_movers.py
```

## 如何贡献

如果你想添加新的 Skill，请参考 `skill-writer` 中的规范进行创建，并将其放置在独立的文件夹中。
