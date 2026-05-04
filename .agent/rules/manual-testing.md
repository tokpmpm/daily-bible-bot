---
description: Testing mechanism for Daily Bible Bot
---

# 手動測試規範 (Manual Testing Mechanism)

為了避免在開發與除錯過程中，意外發送測試推播給所有 LINE 與 Telegram 訂閱用戶，專案已實作 `DRY_RUN` 測試機制。

## 規則
1. 每次進行手動測試或修改程式碼後驗證時，**必須**優先詢問使用者：「是否要在測試時略過實際發送訊息 (Dry Run)?」
2. 若使用者同意（或預設情況下），應透過傳遞 `DRY_RUN` 參數來觸發腳本：
   - **透過 GitHub Actions 手動觸發**：
     使用 GitHub CLI 時，必須加上 `-f dry_run=true`：
     ```bash
     gh workflow run daily_bot.yml --repo tokpmpm/daily-bible-bot -f dry_run=true
     ```
   - **本機端直接執行 Python 腳本**：
     設定環境變數：
     ```bash
     DRY_RUN=true python bot.py
     ```
3. `DRY_RUN=true` 啟動時，程式的運作行為如下：
   - 抓取經文、產生內容、語音合成：**照常執行** (可驗證核心邏輯)。
   - LINE / Telegram 廣播推播：**略過**。
   - Supabase 儲存與 Web Push：**略過**。
   - 終端機 (或 CI Log) 中會印出 `=== Message Content ===` 以及預計發送的 JSON 格式供檢查。
