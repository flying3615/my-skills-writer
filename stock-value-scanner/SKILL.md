---
name: stock-value-scanner
description: 使用 Yahoo Finance 进行股票价值投资分析与趋势查询。
---

# Stock Value Scanner Skill


## Description
这是一个基于价值投资逻辑的股票自动扫描工具。它利用 Yahoo Finance 获取实时财务数据（P/B, P/E, ROE 等），并自动计算评分，判断该股票是否属于“价值洼地”或“高成长股”。

## Features
- **实时估值分析**：自动获取 P/B, P/E, PEG 等核心估值指标 (Yahoo Finance)。
- **股价趋势分析**：查看收盘价、历史高点回撤、52周范围及长期均线趋势。
- **质量体检**：自动检测 ROE, 净利率等质量指标，排除“垃圾股”。
- **智能打分**：基于巴菲特价值投资逻辑生成 0-6 分的综合评分。

## Usage

**前置要求**:
- 必须安装 Python 库 `yfinance`: `pip install yfinance`
- **无需** 任何 API Key。

### Example Prompts
- "分析一下 MARA 的投资价值"
- "看看 AAPL 最近的走势怎么样"
- "查询 NVDA 离历史高点还有多远"
- "扫描科技巨头的估值情况" (使用 `--scan` 参数)

## Execution

### 1. 价值分析 & 评分
```bash
python3 .gemini/skills/stock-value-scanner/scanner.py [SYMBOL]
```
或批量扫描预设列表：
```bash
python3 .gemini/skills/stock-value-scanner/scanner.py --scan
```

### 2. 股价趋势查询
```bash
python3 .gemini/skills/stock-value-scanner/stock_price.py [SYMBOL]
```

## Tips for the Agent
- **场景区分**:
  - 用户问 **“值不值得买”、“基本面”、“估值”** -> 使用 `scanner.py`。
  - 用户问 **“趋势”、“走势”、“历史高点”、“回撤”、“均线”** -> 使用 `stock_price.py`。
- 遇到 `ImportError: No module named 'yfinance'` 错误时，请指导用户运行 `pip install yfinance`。
- 运行结果是文本报告，直接展示给用户即可，无需过度解释。
