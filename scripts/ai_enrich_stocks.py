import json
import os
import time
from google import genai
from google.genai import types

# 檔案路徑設定
JSON_PATH = os.path.join(os.path.dirname(__file__), "../src/data/stocks.json")

# 初始化 Gemini API Client
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("⚠️ 請先設定 GEMINI_API_KEY 環境變數！\n例如 (PowerShell): $env:GEMINI_API_KEY='你的金鑰'")

client = genai.Client(api_key=api_key)

# 專用高額度現役模型清單（避開每日僅 20 次限制的主力模型）
HIGH_QUOTA_MODELS = [
    'gemini-3.5-flash-lite',
    'gemini-3.1-flash',
    'gemini-3.1-flash-lite'
]

def get_working_model():
    """自動查詢此 API 金鑰支援的高額度 Gemini 模型"""
    print("🔍 正在自動偵測您的 API 金鑰可用的高額度 Gemini 模型...")
    try:
        available_models = []
        for m in client.models.list():
            name = m.name.replace("models/", "")
            if any(k in name for k in ["flash", "pro"]):
                available_models.append(name)
        
        print(f"✅ 帳號可用模型清單：{available_models}")
        
        for preferred in HIGH_QUOTA_MODELS:
            if preferred in available_models:
                print(f"🎯 選用高額度最佳模型：{preferred}\n")
                return preferred
        
        # 備用過濾：過濾掉 20 次/天限制的模型與舊版模型
        valid_models = [
            m for m in available_models 
            if not any(ex in m for ex in ["2.5", "1.5", "2.0", "3.8", "3.6"]) and m != "gemini-3.5-flash"
        ]
        if valid_models:
            print(f"🎯 選用模型：{valid_models[0]}\n")
            return valid_models[0]
            
    except Exception as e:
        print(f"⚠️ 自動偵測模型失敗 ({e})，預設使用 gemini-3.5-flash-lite\n")
    
    return 'gemini-3.5-flash-lite'

def load_stocks():
    if not os.path.exists(JSON_PATH):
        raise FileNotFoundError(f"找不到資料庫檔案：{JSON_PATH}")
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_stocks(data):
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def query_ai_for_supply_chain(model_name: str, symbol: str, name: str, sector: str, max_retries: int = 2):
    """呼叫 Gemini API 取得數據（僅在高額度模型間切換）"""
    prompt = f"""
請作為專業的台灣股市與產業分析師，提供「{name} ({symbol})」[所屬產業：{sector}] 的產業簡介與上下游供應鏈關係。

請嚴格遵循以下 JSON 格式回覆（不要加入任何 markdown 標記或額外文字）：
{{
  "description": "簡短 1-2 句話說明該公司核心業務與市場地位",
  "upstream": [
    {{"name": "關鍵上游公司或原料供應商名稱", "note": "供應產品或服務範疇"}}
  ],
  "downstream": [
    {{"name": "主要核心客戶或下游應用領域名稱", "note": "合作或採購項目"}}
  ]
}}

注意事項：
1. 上上下游公司名稱盡量優先使用台灣上市櫃公司名稱（如：台積電、華新、中鋼）或國際知名大廠（如：Apple, NVIDIA, Tesla）。
2. 若該產業無明顯公開之單一客戶/供應商，請填寫主要產業類別（例如：「營建工程廠」、「台電電網計畫」）。
3. upstream 與 downstream 各提供 2 至 4 個最主要的項目即可。
"""

    # 備用切換只使用高額度模型
    models_to_try = [model_name] + [m for m in HIGH_QUOTA_MODELS if m != model_name]

    for current_model in models_to_try:
        for attempt in range(1, max_retries + 1):
            try:
                response = client.models.generate_content(
                    model=current_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.2
                    )
                )
                return json.loads(response.text)
            except Exception as e:
                err_msg = str(e)
                if "503" in err_msg or "UNAVAILABLE" in err_msg:
                    print(f"  ⚠️ 模型 {current_model} 伺服器繁忙 (503)，改嘗試備用高額度模型...")
                    time.sleep(1.5)
                    break
                elif "404" in err_msg or "NOT_FOUND" in err_msg:
                    break
                
                if attempt < max_retries:
                    time.sleep(attempt * 2)
                else:
                    print(f"  ❌ {current_model} 失敗 ({symbol} {name}): {e}")

    return None

def batch_enrich_stocks(max_items: int = 100, delay_seconds: float = 2.0):
    """批次補全缺乏上下游資料的股票"""
    model_name = get_working_model()
    stocks = load_stocks()
    
    pending_list = [
        (s_id, s_info) for s_id, s_info in stocks.items()
        if not s_info.get("upstream") and not s_info.get("downstream")
    ]
    
    total_pending = len(pending_list)
    print(f"📊 目前資料庫共有 {len(stocks)} 檔股票，其中 {total_pending} 檔缺乏上下游資料。")
    
    if total_pending == 0:
        print("✨ 所有股票已有上下游資料，無需更新！")
        return

    target_count = min(max_items, total_pending)
    print(f"🚀 本次預計處理前 {target_count} 檔...\n")
    
    processed_count = 0
    success_count = 0

    for symbol, info in pending_list[:max_items]:
        processed_count += 1
        name = info.get("name", "未知公司")
        sector = info.get("sector", "上市櫃股票")
        
        print(f"[{processed_count}/{target_count}] 正在處理：{symbol} {name} ({sector})...")
        
        result = query_ai_for_supply_chain(model_name, symbol, name, sector)
        if result:
            stocks[symbol]["description"] = result.get("description", info.get("description", ""))
            stocks[symbol]["upstream"] = result.get("upstream", [])
            stocks[symbol]["downstream"] = result.get("downstream", [])
            success_count += 1
            print(f"  ✅ 完成：上游 {len(result.get('upstream', []))} 項 / 下游 {len(result.get('downstream', []))} 項")
            
            if success_count % 5 == 0:
                save_stocks(stocks)
                print("  💾 已即時儲存進度至 stocks.json")
        
        time.sleep(delay_seconds)

    save_stocks(stocks)
    print(f"\n🎉 批次處理完畢！成功更新 {success_count} 檔股票，已全數儲存至 stocks.json。")

if __name__ == "__main__":
    batch_enrich_stocks(max_items=100, delay_seconds=2.0)