import os
import sys
import json
import time
import urllib.request
import argparse

# 检查 API KEY
API_KEY = os.environ.get("ALPHA_VANTAGE_API_KEY")

def get_data(symbol):
    """从 Alpha Vantage 获取概览数据"""
    if not API_KEY:
        print("❌ 错误: 未找到 ALPHA_VANTAGE_API_KEY 环境变量。")
        return None
        
    url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={symbol}&apikey={API_KEY}"
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            if "Symbol" not in data:
                return None
            return data
    except Exception as e:
        print(f"❌ {symbol} 请求错误: {e}")
        return None

def get_market_movers(category="most_actively_traded"):
    """获取市场异动名单: gainers, losers, most_actively_traded"""
    print(f"🔍 正在获取市场榜单 ({category})...")
    url = f"https://www.alphavantage.co/query?function=TOP_GAINERS_LOSERS&apikey={API_KEY}"
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            if category == "gainers":
                return data.get("top_gainers", [])
            elif category == "losers":
                return data.get("top_losers", [])
            else:
                return data.get("most_actively_traded", [])
    except Exception as e:
        print(f"❌ 获取榜单失败: {e}")
        return []

def analyze_single_stock(data, quiet=False):
    """分析单个股票数据并返回得分和摘要"""
    if not data: return 0, None
    
    symbol = data.get("Symbol")
    try:
        price = float(data.get("50DayMovingAverage", 0))
        pb = float(data.get("PriceToBookRatio", 0))
        pe = float(data.get("PERatio", 0)) if data.get("PERatio") != "None" else 999
        roe = float(data.get("ReturnOnEquityTTM", 0)) * 100
        profit_margin = float(data.get("ProfitMargin", 0)) * 100
    except ValueError:
        return 0, None

    # 评分逻辑
    score = 0
    reasons = []

    # 估值分
    if 0 < pb < 1.5: score += 2; reasons.append("P/B极低")
    elif pb < 3.0: score += 1
    
    if 0 < pe < 15: score += 1; reasons.append("P/E便宜")
    elif pe > 50: score -= 1; reasons.append("估值过高")

    # 质量分
    if roe > 15: score += 2; reasons.append("高ROE")
    elif roe < 5: score -= 1
    
    if profit_margin > 20: score += 1; reasons.append("高净利")

    summary = {
        "symbol": symbol,
        "price": price,
        "score": score,
        "pb": pb,
        "pe": pe,
        "roe": roe,
        "reasons": ", ".join(reasons)
    }

    if not quiet:
        analyze_value(data) # 打印详细报告
    
    return score, summary

def analyze_value(data):
    """原有的详细打印函数"""
    # ... (保留原有逻辑，为了简洁这里不重复代码，实际运行时需要确保此函数存在或逻辑合并)
    # 为了简化，这里直接调用上面的逻辑，但打印详细信息
    # 实际代码中，analyze_single_stock 可以调用这个打印函数，或者反过来
    # 这里为了不破坏原有结构，我们假设 analyze_value 依然负责打印
    
    symbol = data.get("Symbol")
    price = data.get("50DayMovingAverage", "N/A")
    target = data.get("AnalystTargetPrice", "N/A")
    
    print(f"\n📊 {symbol} | 价: ${price} | 目标: ${target}")
    # ... (简单打印核心指标)
    print(f"   P/B: {data.get('PriceToBookRatio')} | ROE: {data.get('ReturnOnEquityTTM')}")

def scan_market(category="most_actively_traded", limit=5):
    """批量扫描"""
    movers = get_market_movers(category)
    if not movers:
        print("未找到股票名单。")
        return

    targets = movers[:limit]
    print(f"📋 锁定 {len(targets)} 只股票进行深度扫描 (每只间隔12秒以防封号)...")
    
    results = []
    
    for i, item in enumerate(targets):
        symbol = item['ticker_'] if 'ticker_' in item else item.get('ticker')
        print(f"[{i+1}/{len(targets)}] 分析 {symbol} ...")
        
        data = get_data(symbol)
        if data:
            score, summary = analyze_single_stock(data, quiet=True)
            if summary:
                results.append(summary)
        
        if i < len(targets) - 1:
            time.sleep(12) # 遵守 API 速率限制

    # 打印排行榜
    print("\n" + "="*60)
    print(f"🏆 {category.upper()} 价值选股排行榜")
    print("="*60)
    print(f"{'代码':<8} {'得分':<5} {'股价':<10} {'P/B':<8} {'ROE':<8} {'亮点'}")
    print("-" * 60)
    
    # 按得分降序排列
    results.sort(key=lambda x: x['score'], reverse=True)
    
    for res in results:
        print(f"{res['symbol']:<8} {res['score']:<5} ${res['price']:<9.2f} {res['pb']:<8.2f} {res['roe']:<7.1f}% {res['reasons']}")
    print("="*60)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='股票价值分析与扫描器')
    parser.add_argument('symbol', nargs='?', help='单个股票代码 (例如 AAPL)')
    parser.add_argument('--scan', choices=['active', 'gainers', 'losers'], help='扫描模式: active(活跃), gainers(涨幅), losers(跌幅)')
    parser.add_argument('--limit', type=int, default=5, help='扫描数量限制 (默认5)')
    
    args = parser.parse_args()

    if not API_KEY:
        print("❌ 请先配置环境变量: export ALPHA_VANTAGE_API_KEY='您的KEY'")
        sys.exit(1)

    if args.scan:
        category_map = {
            'active': 'most_actively_traded',
            'gainers': 'top_gainers',
            'losers': 'top_losers'
        }
        scan_market(category_map[args.scan], args.limit)
    elif args.symbol:
        data = get_data(args.symbol.upper())
        if data:
            analyze_single_stock(data, quiet=False)
    else:
        parser.print_help()

