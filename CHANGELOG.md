# Changelog

All notable changes to this project will be documented in this file.

## [2026-05-31] - Podcast episode description 排版
### Changed
- Podcast episode description 改成「今日經文 / 靈修默想 / 今日禱告」三段式格式，並移除 RSS 中重複出現的開頭經文段落。
- Episode RSS 新增 `content:encoded` HTML 版本，保留 `description` 與 `itunes:summary` 的純文字版本，提升 Apple Podcasts 與其他 podcast app 的 show notes 顯示相容性。
- Podcast cover 圖中文字更新為「安靜三分鐘」。
- **驗證結果**: 已部署 Cloudflare Worker version `f8ef795d-e9d5-44c8-a2c9-b00a921a69b5`；正式環境 `/feed.rss` 與 `/podcast.xml` 均回傳新版 episode description 排版。

## [2026-05-30] - Podcast RSS .rss 別名
### Fixed
- **現狀**: Apple Podcasts Connect 使用者嘗試改填 `https://daily-bible-bot-trigger.tokpmpm.workers.dev/feed.rss` 時，Worker 原先回傳 404；修正 `.rss` GET 後，節目仍長時間停在「處理節目詳細資訊」。
- **根本原因 (Root Cause)**: Cloudflare Worker 僅實作 `/podcast.xml` 的 GET RSS 路由，尚未提供 `.rss` 結尾的 feed URL 別名；且 Apple 可能使用 HEAD 預先探測 RSS，但 `/podcast.xml` 與 `/feed.rss` 的 HEAD 請求仍回傳 404。
- **修正方案**: 將 Podcast RSS 路由擴充為同時支援 `/podcast.xml` 與 `/feed.rss` 的 GET/HEAD，兩者共用同一個 `podcastFeedResponse()` 輸出；HEAD 回應保留 RSS headers 與 Content-Length，但不回傳 body。
- **驗證結果**: 已部署 Cloudflare Worker version `f5ca917d-c5de-4251-8402-361c047eb051`；正式環境 `/feed.rss` 與 `/podcast.xml` 均回傳新頻道名稱「安靜三分鐘」與新頻道介紹，且 `atom:link rel="self"` 會依實際請求分別指向 `/feed.rss` 或 `/podcast.xml`。

### Changed
- 將 Podcast 頻道名稱改為「安靜三分鐘」，頻道介紹改為「每日 3 分鐘，陪你在聲音裡安靜、聆聽、禱告，把分散的心重新對齊神。」。

## [2026-05-27] - Podcast RSS 與 Cloudflare R2 音檔儲存
### Added
- 新增 Cloudflare R2 作為正式音檔儲存來源，LINE、Telegram、網站播放器與 Podcast RSS 共用同一個公開 MP3 URL。
- 新增 Cloudflare Worker 安全上傳入口，GitHub Actions 不需保存 R2 S3 secret。
- Cloudflare Worker 新增 `/podcast.xml`，從 Supabase 讀取每日內容並輸出標準 Podcast RSS feed。
- Supabase `daily_bible` 新增 podcast metadata 欄位：`audio_duration_ms`、`audio_size_bytes`、`podcast_guid`、`published_at`。

### Changed
- 移除主流程對 Catbox 與 Supabase Storage 的音檔上傳依賴。
- GitHub Actions 新增 Worker audio upload 所需 secrets。

## [2026-05-04] - 手動測試安全機制 (Dry Run)
### Added
- **新增功能**: 在 Python 腳本層級加入完整的 `DRY_RUN` 支援，避免測試時干擾實際用戶。
  - 當設定 `DRY_RUN=true` 時，將會跳過傳送 LINE 訊息、Telegram 推播、Supabase 儲存與 Web Push 廣播。
  - 終端機與 CI logs 會印出 `=== Message Content ===` 的 JSON 格式內容以供除錯。
- **新增規則**: 新增 `.agent/rules/manual-testing.md` 文件。未來 AI 助理在進行手動測試或執行時，會強制先詢問使用者是否要啟動 Dry Run，預設避免意外發送推播。
### Fixed
- **現狀**: 前次執行手動測試時，雖然傳遞了 `dry_run: true` 參數給 GitHub Actions，但由於原本 Python 程式缺乏對此環境變數的判斷，導致仍發出了 LINE 訊息。
- **根本原因 (Root Cause)**: 原有防呆機制僅檢查 `LINE_CHANNEL_ACCESS_TOKEN` 是否等於 `"your_line_channel_access_token"` 或為空值。但 GitHub Actions expression 傳入空字串的行為無法完全攔截執行。
- **修正方案**: 讓 `bot.py` 明確讀取 `DRY_RUN` 環境變數，當其為 `true` 時，在各個推播與寫入服務前進行短路 (Short-circuit) 攔截。
- **驗證結果**: 透過修改程式碼並 push 至遠端，確定此邏輯可成功攔截不必要的外部服務請求。

## [2026-05-04] - Email 通知條件語法修復
### Fixed
- **現狀**: Email 成功通知步驟的 `if` 條件含有錯誤語法 `env.BOT_STATUS == 'success'`，可能導致條件判斷失效。
- **根本原因 (Root Cause)**: `env.BOT_STATUS` 在 GitHub Actions expression 中必須使用 `${{ env.BOT_STATUS }}` 語法引用，且該變數只在前一 step 的 `run` 腳本中設定，存在競爭條件。
- **修正方案**:
  1. 移除 `if: success() && env.BOT_STATUS == 'success'` 中多餘的 `env.BOT_STATUS` 條件，直接使用 `if: success()`（GitHub Actions 的 `success()` 函數本身即正確追蹤所有前置 step 的狀態）。
  2. 清除 `Run Daily Bot` step 中多餘的 `echo "BOT_STATUS=success" >> $GITHUB_ENV`。
- **驗證結果**: YAML 語法驗證通過，通知邏輯符合 GitHub Actions 官方建議。

## [2026-05-04] - Email 執行通知
### Added
- **新增功能**: 在 `daily_bot.yml` 加入成功/失敗 Email 通知（透過 `dawidd6/action-send-mail@v3`）。
  - 成功時：寄出包含執行摘要與 Actions 連結的通知信。
  - 失敗時：立即寄出警示信，提醒點擊查看錯誤日誌。
- **新增 Skill**: 建立 `github-actions-email-notify` 可重用 Skill，未來任何專案加入 Email 通知只需套用此範本。
- **順帶升級**: `actions/checkout@v3` → `v4`，`setup-python@v4` → `v5`，Python 版本 `3.9` → `3.11`。
- **所需 Secrets**: 需在 Repository 中手動新增 `EMAIL_SENDER` 與 `EMAIL_PASSWORD`。

## [2026-05-04] - Scraper 重構
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
