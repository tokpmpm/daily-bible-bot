"""
Daily Bible Bot - Test Script (No LINE Sending)
測試生成靈修短文和音檔，但不送到 LINE 官方帳號
"""
import sys
from scraper import get_daily_verse
from content_gen import generate_exposition
from audio_gen import generate_audio

def main():
    print("\n" + "="*60)
    print("🧪 Daily Bible Bot - 測試模式")
    print("="*60 + "\n")
    
    # Step 1: Scrape today's verse
    print("📖 步驟 1: 抓取今日經文...")
    verse_data = get_daily_verse()
    
    if not verse_data:
        print("❌ 無法抓取經文")
        return
    
    print(f"✅ 經文抓取成功:")
    print(f"   出處: {verse_data['reference']}")
    print(f"   內容: {verse_data['text']}\n")
    
    # Step 2: Generate exposition
    print("✍️  步驟 2: 生成靈修短文 (350字)...")
    exposition = generate_exposition(verse_data)
    
    if not exposition:
        print("❌ 無法生成靈修短文")
        return
    
    print("✅ 靈修短文生成成功\n")
    print("-"*60)
    print("📝 靈修短文內容:")
    print("-"*60)
    print(exposition)
    print("-"*60)
    print(f"字數: {len(exposition)} 字\n")
    
    # Step 3: Generate audio
    print("🎙️  步驟 3: 生成音檔 (OpenAI TTS - nova)...")
    audio_path = generate_audio(exposition, "test_daily_message.mp3")
    
    if not audio_path:
        print("❌ 無法生成音檔")
        return
    
    print(f"✅ 音檔生成成功: {audio_path}\n")
    
    # Summary
    print("="*60)
    print("✅ 測試完成！")
    print("="*60)
    print(f"📁 音檔位置: {audio_path}")
    print(f"📝 靈修短文字數: {len(exposition)} 字")
    print(f"🎙️  使用聲音: OpenAI TTS - nova")
    print("="*60)

if __name__ == "__main__":
    main()
