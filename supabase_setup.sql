-- =====================================================
-- Supabase 資料表設定 for Daily Bible Subscription
-- 請在 Supabase SQL Editor 中執行此 SQL
-- =====================================================

-- 1. 每日解經資料表
CREATE TABLE IF NOT EXISTS daily_bible (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    verse_text TEXT NOT NULL,
    verse_reference TEXT NOT NULL,
    exposition TEXT NOT NULL,
    audio_url TEXT DEFAULT '',
    view_count INTEGER DEFAULT 0,
    play_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Push 訂閱者資料表
CREATE TABLE IF NOT EXISTS push_subscribers (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    subscription JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. 遞增瀏覽量函數
CREATE OR REPLACE FUNCTION increment_view(row_id UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE daily_bible SET view_count = view_count + 1 WHERE id = row_id;
END;
$$ LANGUAGE plpgsql;

-- 4. 遞增播放數函數
CREATE OR REPLACE FUNCTION increment_play(row_id UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE daily_bible SET play_count = play_count + 1 WHERE id = row_id;
END;
$$ LANGUAGE plpgsql;

-- 5. 啟用 Row Level Security
ALTER TABLE daily_bible ENABLE ROW LEVEL SECURITY;
ALTER TABLE push_subscribers ENABLE ROW LEVEL SECURITY;

-- 6. 設定存取權限

-- 允許公開讀取 daily_bible
CREATE POLICY "Public read daily_bible" ON daily_bible
    FOR SELECT USING (true);

-- 允許服務端寫入 daily_bible
CREATE POLICY "Service insert daily_bible" ON daily_bible
    FOR INSERT WITH CHECK (true);

-- 允許更新瀏覽/播放次數
CREATE POLICY "Public update daily_bible counts" ON daily_bible
    FOR UPDATE USING (true) WITH CHECK (true);

-- 允許公開新增訂閱者
CREATE POLICY "Public insert subscribers" ON push_subscribers
    FOR INSERT WITH CHECK (true);

-- 允許服務端讀取訂閱者
CREATE POLICY "Service read subscribers" ON push_subscribers
    FOR SELECT USING (true);

-- 允許公開呼叫 RPC 函數
GRANT EXECUTE ON FUNCTION increment_view(UUID) TO anon;
GRANT EXECUTE ON FUNCTION increment_play(UUID) TO anon;
