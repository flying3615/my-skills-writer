---
name: macro-market-report
description: Use when the user wants a cross-asset macro market snapshot with commodities, equity indices, dollar, Treasury yields, and crypto prices plus percentage changes
---

# Macro Market Report

生成一份中文宏观市场报表，默认覆盖商品、股指、波动率、美元外汇、美债收益率和主流加密资产，并输出最新价格与 `1日 / 5日 / 1个月` 涨跌幅。

## 前置要求

- 需要 `python3`
- 需要安装 `yfinance`
- 如未安装，运行 `pip install yfinance`

## 适用场景

- 用户想看“今天宏观市场怎么样”
- 用户想快速查看黄金、原油、美元、美债、BTC、ETH 等关键资产
- 用户需要一个可直接阅读或转发的终端报表，而不是零散单品种查询

## 默认监控资产

- 商品：WTI 原油、布伦特原油、黄金、白银、天然气、铜
- 股指：标普 500、纳指、道指、罗素 2000
- 波动率：VIX
- 外汇：美元指数、欧元/美元、美元/日元
- 美债：13 周、5 年、10 年、30 年美债收益率
- 加密：BTC、ETH

## 示例触发语

- “给我一份今天的宏观市场报表”
- “看一下黄金原油美元美债和 BTC 的最新变化”
- “生成一份跨资产市场快报”

## 执行

默认报表：

```bash
python3 macro-market-report/scripts/market_report.py
```

附加自定义 ticker：

```bash
python3 macro-market-report/scripts/market_report.py --extra "TLT,SLV,SOL-USD"
```

## 使用说明

- 优先直接运行脚本并展示报表结果
- 不要依赖 `info` 字段解释走势，报表里的涨跌幅以历史收盘价计算为准
- 如果个别 ticker 失败，继续展示其余资产，并把失败项列在报表末尾
- 如果用户只想加入额外监控标的，使用 `--extra`
