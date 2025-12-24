"""
TTS Voice Demo - 繁體中文聲音試聽
生成多個免費 TTS 服務的語音樣本供比較
"""
import asyncio
import edge_tts
import os

# 測試文字 - 使用聖經內容
TEST_TEXT = """
這是每日聖經靈修的測試語音。
神賜給我們，不是膽怯的心，乃是剛強、仁愛、謹守的心。
願主的平安與你同在，阿門。
"""

# Edge TTS 台灣繁體中文聲音選項
EDGE_VOICES = [
    ("zh-TW-HsiaoChenNeural", "曉臻 (女聲, 自然溫柔)"),
    ("zh-TW-HsiaoYuNeural", "曉雨 (女聲, 清新活潑)"),
    ("zh-TW-YunJheNeural", "雲哲 (男聲, 成熟穩重)"),
]

async def generate_edge_tts_demo():
    """使用 Edge TTS 生成多個聲音樣本"""
    output_dir = "voice_demos"
    os.makedirs(output_dir, exist_ok=True)
    
    print("=" * 60)
    print("🎤 Edge TTS 繁體中文(台灣)聲音試聽")
    print("=" * 60)
    print(f"\n測試文字:\n{TEST_TEXT}")
    print("-" * 60)
    
    for voice_id, voice_name in EDGE_VOICES:
        output_file = os.path.join(output_dir, f"edge_{voice_id}.mp3")
        print(f"\n生成中: {voice_name} ({voice_id})...")
        
        try:
            communicate = edge_tts.Communicate(TEST_TEXT.strip(), voice_id)
            await communicate.save(output_file)
            print(f"  ✅ 已生成: {output_file}")
        except Exception as e:
            print(f"  ❌ 失敗: {e}")
    
    print("\n" + "=" * 60)
    print("📁 所有音檔已生成在 voice_demos/ 資料夾")
    print("=" * 60)

async def list_all_chinese_voices():
    """列出所有可用的中文聲音"""
    print("\n" + "=" * 60)
    print("📋 所有可用的中文聲音列表")
    print("=" * 60)
    
    voices = await edge_tts.list_voices()
    chinese_voices = [v for v in voices if v["Locale"].startswith("zh-")]
    
    # 按地區分組
    tw_voices = [v for v in chinese_voices if "TW" in v["Locale"]]
    cn_voices = [v for v in chinese_voices if "CN" in v["Locale"]]
    hk_voices = [v for v in chinese_voices if "HK" in v["Locale"]]
    
    print("\n🇹🇼 台灣 (zh-TW):")
    for v in tw_voices:
        print(f"  - {v['ShortName']}: {v['Gender']}")
    
    print("\n🇨🇳 大陸 (zh-CN):")
    for v in cn_voices:
        print(f"  - {v['ShortName']}: {v['Gender']}")
    
    print("\n🇭🇰 香港 (zh-HK):")
    for v in hk_voices:
        print(f"  - {v['ShortName']}: {v['Gender']}")

async def main():
    # 生成試聽樣本
    await generate_edge_tts_demo()
    
    # 列出所有可用聲音
    await list_all_chinese_voices()
    
    print("\n" + "=" * 60)
    print("💡 試聽完成後，您可以選擇喜歡的聲音")
    print("   然後我可以幫您更新 audio_gen.py 使用該聲音")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
