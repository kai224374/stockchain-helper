import json
import os
import requests

# 取得 stocks.json 的絕對路徑
JSON_PATH = os.path.join(os.path.dirname(__file__), "../src/data/stocks.json")

# 設定要比對監控的熱門台股 ETF 清單
ETF_MAP = {
    "0050": "0050 富邦台50",
    "0056": "0056 元大高股息",
    "00878": "00878 國泰永續高股息",
    "00713": "00713 元大高股息低波動",
    "00919": "00919 群益台灣精選高息",
    "009816": "009816 凱基台灣TOP50"
}

def fetch_latest_etf_holdings():
    """從 FinMind 公開 API 自動抓取最新 ETF 持股資料"""
    etf_stock_mapping = {}  # 紀錄 股票代號 -> 持有它的 ETF 清單

    print("🔍 開始從公開 API 抓取最新 ETF 持股成分...")
    for etf_code, etf_name in ETF_MAP.items():
        try:
            url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockHoldingSharesPer&data_id={etf_code}"
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                data = res.json().get("data", [])
                if data:
                    # 取得最新一期的持股名單
                    latest_date = data[-1].get("date")
                    latest_holdings = [item for item in data if item.get("date") == latest_date]
                    
                    for item in latest_holdings:
                        stock_code = str(item.get("link_id") or item.get("target_code", ""))
                        if stock_code:
                            if stock_code not in etf_stock_mapping:
                                etf_stock_mapping[stock_code] = []
                            if etf_name not in etf_stock_mapping[stock_code]:
                                etf_stock_mapping[stock_code].append(etf_name)
        except Exception as e:
            print(f"⚠️ 抓取 ETF {etf_code} 失敗: {e}")

    return etf_stock_mapping

def update_stocks_json():
    if not os.path.exists(JSON_PATH):
        print(f"❌ 錯誤：找不到資料庫檔案 {JSON_PATH}")
        return

    # 讀取現有 stocks.json
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        stocks = json.load(f)

    # 取得最新 ETF 關係圖
    etf_mapping = fetch_latest_etf_holdings()

    updated_count = 0
    for symbol, stock_info in stocks.items():
        if symbol in etf_mapping and etf_mapping[symbol]:
            # 保留原本手動設定的基金/美股 ETF，更新台股重點 ETF
            current_etfs = stock_info.get("relatedETFs", [])
            preserved = [e for e in current_etfs if not any(code in e for code in ETF_MAP)]
            
            # 合併並去重
            new_etfs = list(dict.fromkeys(preserved + etf_mapping[symbol]))
            stock_info["relatedETFs"] = new_etfs
            updated_count += 1
            print(f"✅ 已自動更新 {stock_info['name']} ({symbol}) 的 ETF 成分股：{new_etfs}")

    # 寫回 stocks.json
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(stocks, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 自動更新完成！共更新 {updated_count} 檔股票的持股數據。")

if __name__ == "__main__":
    update_stocks_json()