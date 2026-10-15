import json
import os
import requests

# 取得 stocks.json 的絕對路徑
JSON_PATH = os.path.join(os.path.dirname(__file__), "../src/data/stocks.json")

# 主要監控並分析持股成分的熱門 ETF 清單
ETF_MAP = {
    "0050": "0050 富邦台50",
    "0056": "0056 元大高股息",
    "00878": "00878 國泰永續高股息",
    "00713": "00713 元大高股息低波動",
    "00919": "00919 群益台灣精選高息",
    "00929": "00929 復華台灣科技優息",
    "00940": "00940 元大台灣價值高息",
    "009816": "009816 凱基台灣TOP50"
}

def fetch_all_taiwan_stocks():
    """從 FinMind 抓取全台灣所有上市櫃股票與 ETF 清單"""
    print("🌐 正在抓取全台股與 ETF 清單...")
    url = "https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockInfo"
    try:
        res = requests.get(url, timeout=15)
        if res.status_code == 200:
            data = res.json().get("data", [])
            # 過濾普通股與 ETF (排除認購權證等無關標的)
            valid_stocks = {}
            for item in data:
                stock_id = item.get("stock_id", "").strip()
                stock_name = item.get("stock_name", "").strip()
                industry = item.get("industry_category", "其他")
                
                # 只保留代號為數字的股票與 ETF (排除特種股/權證)
                if stock_id and stock_name and (stock_id.isdigit() or len(stock_id) == 6):
                    valid_stocks[stock_id] = {
                        "name": stock_name,
                        "sector": industry if industry else "上市櫃股票"
                    }
            print(f"✅ 成功取得 {len(valid_stocks)} 檔台股與 ETF 資訊！")
            return valid_stocks
    except Exception as e:
        print(f"⚠️ 抓取全台股清單失敗: {e}")
    return {}

def fetch_etf_holdings():
    """抓取重點 ETF 持股明細"""
    etf_stock_mapping = {}
    print("🔍 正在抓取重點 ETF 最新成分股...")
    for etf_code, etf_name in ETF_MAP.items():
        try:
            url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockHoldingSharesPer&data_id={etf_code}"
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                data = res.json().get("data", [])
                if data:
                    latest_date = data[-1].get("date")
                    latest_holdings = [item for item in data if item.get("date") == latest_date]
                    for item in latest_holdings:
                        stock_code = str(item.get("link_id") or item.get("target_code", "")).strip()
                        if stock_code:
                            if stock_code not in etf_stock_mapping:
                                etf_stock_mapping[stock_code] = []
                            if etf_name not in etf_stock_mapping[stock_code]:
                                etf_stock_mapping[stock_code].append(etf_name)
        except Exception as e:
            print(f"⚠️ 抓取 ETF {etf_code} 失敗: {e}")
    return etf_stock_mapping

def sync_full_market_data():
    # 讀取既有 stocks.json
    stocks_db = {}
    if os.path.exists(JSON_PATH):
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            try:
                stocks_db = json.load(f)
            except Exception:
                stocks_db = {}

    all_market_stocks = fetch_all_taiwan_stocks()
    etf_mapping = fetch_etf_holdings()

    new_added = 0
    updated_etfs = 0

    # 1. 併入全台股標的 (保留既有的上下游數據)
    for symbol, info in all_market_stocks.items():
        if symbol not in stocks_db:
            stocks_db[symbol] = {
                "symbol": symbol,
                "name": info["name"],
                "sector": info["sector"],
                "description": f"台灣上市/上櫃個股 ({info['sector']})",
                "upstream": [],
                "downstream": [],
                "relatedETFs": []
            }
            new_added += 1
        else:
            # 補齊基本屬性
            stocks_db[symbol]["name"] = info["name"]
            if not stocks_db[symbol].get("sector"):
                stocks_db[symbol]["sector"] = info["sector"]

    # 2. 更新 ETF 持股關係
    for symbol, stock_info in stocks_db.items():
        if symbol in etf_mapping:
            current_etfs = stock_info.get("relatedETFs", [])
            # 保留非預設清單中的 ETF/基金，更新重點 ETF
            preserved = [e for e in current_etfs if not any(code in e for code in ETF_MAP)]
            new_etfs = list(dict.fromkeys(preserved + etf_mapping[symbol]))
            stock_info["relatedETFs"] = new_etfs
            updated_etfs += 1

    # 寫回 stocks.json
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(stocks_db, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 市場同步完成！")
    print(f"新增全台股建檔: {new_added} 檔")
    print(f"更新 ETF 成分股數據: {updated_etfs} 檔股票")
    print(f"目前資料庫總股票數: {len(stocks_db)} 檔")

if __name__ == "__main__":
    sync_full_market_data()