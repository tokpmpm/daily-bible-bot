# Changelog

All notable changes to this project will be documented in this file.

## [2026-05-04]
### Fixed
- **現狀**: 雖然修復了 GitHub Actions 排程，但每天解經機器人依然沒有推播訊息。
- **根本原因 (Root Cause)**: `YouVersion (bible.com)` 網站更改了前端架構（改為動態渲染 Single Page Application），原先 `scraper.py` 使用 `BeautifulSoup` 解析靜態 HTML 的方式失效，導致無法正確抓取「每日經文」。
- **修正方案**:
  1. 重構 `scraper.py`，改為解析 `__NEXT_DATA__` JSON 物件以獲取當日經文章節。
  2. 整合 `bible-api.com` 作為繁體中文經文（CUV 和合本）的備用提取來源，並實作中英書卷名稱的字典對應 (Mapping)。
- **驗證結果**: 手動執行 `scraper.py` 確認已能成功抓取包含經文、出處與圖片的字典資料。

## [2026-04-28]
### Fixed
- **現狀**: 每天解經機器人自二月初以來停止發送訊息。
- **根本原因 (Root Cause)**: GitHub Actions 預設在儲存庫連續 60 天無活動 (commits) 時，會自動停用所有排程的工作流程 (Scheduled workflows)。因專案穩定無須修改，觸發了此限制。
- **修正方案**:
  1. 使用 GitHub CLI (`gh workflow enable`) 手動重新啟用被停用的工作流程 `daily_bot.yml`。
  2. 新增 `keepalive.yml` 工作流程，透過 `gautamkrishnar/keepalive-workflow` 定期發送 API 請求，維持儲存庫的活躍狀態，防止未來再次被自動停用。
- **驗證結果**: 工作流程已確認重啟，且 `keepalive.yml` 已加入版本控制。
