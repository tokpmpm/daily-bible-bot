# Changelog

All notable changes to this project will be documented in this file.

## [2026-04-28]
### Fixed
- **現狀**: 每天解經機器人自二月初以來停止發送訊息。
- **根本原因 (Root Cause)**: GitHub Actions 預設在儲存庫連續 60 天無活動 (commits) 時，會自動停用所有排程的工作流程 (Scheduled workflows)。因專案穩定無須修改，觸發了此限制。
- **修正方案**:
  1. 使用 GitHub CLI (`gh workflow enable`) 手動重新啟用被停用的工作流程 `daily_bot.yml`。
  2. 新增 `keepalive.yml` 工作流程，透過 `gautamkrishnar/keepalive-workflow` 定期發送 API 請求，維持儲存庫的活躍狀態，防止未來再次被自動停用。
- **驗證結果**: 工作流程已確認重啟，且 `keepalive.yml` 已加入版本控制。
