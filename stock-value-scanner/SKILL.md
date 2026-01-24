# Stock Value Scanner Skill

## Description
这是一个基于价值投资逻辑的股票自动扫描工具。它利用 Alpha Vantage API 获取实时财务数据（P/B, P/E, ROE 等），并自动计算评分，判断该股票是否属于“价值洼地”或“高成长股”。

## Features
- **实时估值分析**：自动获取 P/B, P/E, PEG 等核心估值指标 (Alpha Vantage)。
- **实时股价查询**：直接从 Yahoo Finance 获取最新股价，无需 API Key。
- **质量体检**：自动检测 ROE, 净利率等质量指标，排除“垃圾股”。
- **智能打分**：基于巴菲特价值投资逻辑生成 0-6 分的综合评分。
- **买卖信号**：直接给出“强力推荐”、“值得关注”或“风险警示”的结论。

## Usage
用户只需提供股票代码（Symbol），工具将自动输出分析报告。

**前置要求**:
- 估值分析 (`scanner.py`) 需要配置环境变量 `ALPHA_VANTAGE_API_KEY`。
- 股价查询 (`stock_price.py`) **不需要**任何 API Key。

### Example Prompts
- "分析一下 MARA 的投资价值" (调用 scanner)
- "看看 AAPL 现在多少钱" (调用 stock_price)
- "查询 TSLA 的股价" (调用 stock_price)

## Execution

### 1. 价值分析 (需要 API Key)
```bash
python3 .gemini/skills/stock-value-scanner/scanner.py [SYMBOL]
```

### 2. 股价查询 (无需 API Key)
```bash
python3 .gemini/skills/stock-value-scanner/stock_price.py [SYMBOL]
```

## Tips for the Agent
- 当用户询问某只股票“值不值得买”、“便宜吗”或“基本面如何”时，请使用 `scanner.py`。
- 当用户仅询问“股价”、“多少钱”或“行情”时，优先使用 `stock_price.py`，因为它更快且无需 Key。
- 在运行 `scanner.py` 前，**务必检查** `ALPHA_VANTAGE_API_KEY` 环境变量。
- 运行结果是文本报告，直接展示给用户即可，无需过度解释，除非用户有追问。
