import type { PlasmoCSConfig } from "plasmo"
import { useEffect, useState } from "react"
import localStockData from "./data/stocks.json"

export const config: PlasmoCSConfig = {
  matches: ["<all_urls>"]
}

// 可替換為你自己的 GitHub Raw JSON 連結或伺服器 API 網址
const REMOTE_DATA_URL = "https://raw.githubusercontent.com/kai224374/stockchain-helper/main/src/data/stocks.json"

export default function StockChainOverlay() {
  const [stockDb, setStockDb] = useState<any>(localStockData) // 預設使用本地舊資料
  const [selectedStock, setSelectedStock] = useState<any>(null)
  const [stockHistory, setStockHistory] = useState<any[]>([])
  const [position, setPosition] = useState({ top: 0, left: 0 })
  const [visible, setVisible] = useState(false)

  // 1. 自動背景更新資料庫
  useEffect(() => {
    const fetchLatestData = async () => {
      try {
        const response = await fetch(REMOTE_DATA_URL)
        if (response.ok) {
          const latestData = await response.json()
          setStockDb(latestData) // 成功更新為最新資料
          console.log("[StockChain] 成功同步最新動態供應鏈資料")
        }
      } catch (error) {
        console.warn("[StockChain] 無法連接遠端資料庫，維持使用本地備份資料")
      }
    }

    fetchLatestData()
  }, [])

  // 根據名稱或代號尋找股票資料
  const findStock = (term: string) => {
    if (!term) return null
    const cleanTerm = term.trim().toLowerCase()

    const matchedKey = Object.keys(stockDb).find((key) => {
      const item = (stockDb as any)[key]
      return (
        key.toLowerCase() === cleanTerm ||
        item.symbol.toLowerCase() === cleanTerm ||
        item.name.toLowerCase() === cleanTerm ||
        cleanTerm.includes(item.name.toLowerCase()) ||
        item.name.toLowerCase().includes(cleanTerm)
      )
    })

    return matchedKey ? (stockDb as any)[matchedKey] : null
  }

  useEffect(() => {
    const handleMouseUp = () => {
      const selection = window.getSelection()
      const text = selection?.toString().trim()

      if (!text || text.length < 2) return

      const stock = findStock(text)
      if (stock) {
        const range = selection?.getRangeAt(0)
        const rect = range?.getBoundingClientRect()

        if (rect) {
          setPosition({
            top: rect.bottom + window.scrollY + 8,
            left: rect.left + window.scrollX
          })
          setSelectedStock(stock)
          setStockHistory([stock])
          setVisible(true)
        }
      }
    }

    const handleMouseDown = (e: MouseEvent) => {
      const path = e.composedPath()
      const isInsideCard = path.some(
        (el) => (el as HTMLElement).id === "stockchain-card"
      )

      if (!isInsideCard) {
        setVisible(false)
      }
    }

    document.addEventListener("mouseup", handleMouseUp)
    document.addEventListener("mousedown", handleMouseDown)

    return () => {
      document.removeEventListener("mouseup", handleMouseUp)
      document.removeEventListener("mousedown", handleMouseDown)
    }
  }, [stockDb]) // 當 stockDb 更新時更新監聽邏輯

  const handleStockClick = (name: string) => {
    const stock = findStock(name)
    if (stock) {
      setSelectedStock(stock)
      setStockHistory((prev) => [...prev, stock])
    } else {
      alert(`目前資料庫尚未收錄「${name}」的詳細供應鏈資料。`)
    }
  }

  const handleBack = () => {
    if (stockHistory.length > 1) {
      const newHistory = stockHistory.slice(0, -1)
      setStockHistory(newHistory)
      setSelectedStock(newHistory[newHistory.length - 1])
    }
  }

  if (!visible || !selectedStock) return null

  return (
    <div
      id="stockchain-card"
      style={{
        position: "absolute",
        top: `${position.top}px`,
        left: `${position.left}px`,
        width: "340px",
        backgroundColor: "#ffffff",
        border: "1px solid #cbd5e1",
        borderRadius: "12px",
        boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.15)",
        padding: "16px",
        fontFamily: "system-ui, -apple-system, sans-serif",
        color: "#1e293b",
        zIndex: 999999
      }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "8px"
        }}>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          {stockHistory.length > 1 && (
            <button
              onClick={handleBack}
              style={{
                border: "1px solid #cbd5e1",
                background: "#f8fafc",
                borderRadius: "4px",
                padding: "2px 8px",
                cursor: "pointer",
                fontSize: "11px",
                fontWeight: "bold",
                color: "#475569"
              }}>
              ← 返回
            </button>
          )}
          <span style={{ fontSize: "16px", fontWeight: "bold", color: "#0f172a" }}>
            {selectedStock.name} ({selectedStock.symbol})
          </span>
        </div>
        <span
          style={{
            fontSize: "11px",
            backgroundColor: "#eff6ff",
            color: "#2563eb",
            padding: "2px 6px",
            borderRadius: "4px"
          }}>
          {selectedStock.sector}
        </span>
      </div>

      <p style={{ fontSize: "12px", color: "#64748b", margin: "6px 0 10px 0" }}>
        {selectedStock.description}
      </p>

      <hr style={{ border: "none", borderTop: "1px solid #f1f5f9", margin: "8px 0" }} />

      <div style={{ fontSize: "12px" }}>
        <div style={{ fontWeight: "bold", color: "#334155", marginBottom: "6px" }}>
          🔗 上下游關聯：
        </div>

        {selectedStock.downstream && (
          <div style={{ margin: "4px 0", color: "#475569" }}>
            <span style={{ fontWeight: "600" }}>• 核心客戶：</span>
            {selectedStock.downstream.map((d: any, i: number) => {
              const isAvailable = !!findStock(d.name)
              return (
                <span
                  key={i}
                  onClick={() => handleStockClick(d.name)}
                  style={{
                    color: isAvailable ? "#2563eb" : "#475569",
                    textDecoration: isAvailable ? "underline" : "none",
                    cursor: isAvailable ? "pointer" : "default",
                    fontWeight: isAvailable ? "bold" : "normal"
                  }}>
                  {d.name} ({d.note}){i < selectedStock.downstream.length - 1 ? "、" : ""}
                </span>
              )
            })}
          </div>
        )}

        {selectedStock.upstream && (
          <div style={{ margin: "4px 0", color: "#475569" }}>
            <span style={{ fontWeight: "600" }}>• 關鍵供應商：</span>
            {selectedStock.upstream.map((u: any, i: number) => {
              const isAvailable = !!findStock(u.name)
              return (
                <span
                  key={i}
                  onClick={() => handleStockClick(u.name)}
                  style={{
                    color: isAvailable ? "#2563eb" : "#475569",
                    textDecoration: isAvailable ? "underline" : "none",
                    cursor: isAvailable ? "pointer" : "default",
                    fontWeight: isAvailable ? "bold" : "normal"
                  }}>
                  {u.name} ({u.note}){i < selectedStock.upstream.length - 1 ? "、" : ""}
                </span>
              )
            })}
          </div>
        )}
      </div>

      {selectedStock.relatedETFs && (
        <div style={{ fontSize: "12px", marginTop: "10px" }}>
          <div style={{ fontWeight: "bold", color: "#334155", marginBottom: "4px" }}>
            📊 納入重點 ETF：
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
            {selectedStock.relatedETFs.map((etf: string, i: number) => (
              <span
                key={i}
                style={{
                  fontSize: "11px",
                  backgroundColor: "#f1f5f9",
                  color: "#475569",
                  padding: "2px 6px",
                  borderRadius: "4px"
                }}>
                {etf}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}