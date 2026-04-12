"""VibeVoice 中文语言检测诊断工具

用于深入分析 VibeVoice 为什么会输出非中文音频。

使用方法:
    python3 -m app.tests.diagnose_vibevoice_language
"""

from __future__ import annotations

import asyncio
import logging
import time
import wave
from pathlib import Path

from app.config import AppConfig
from app.tts.qwen_adapter import MLXQwenTTSAdapter


# 配置详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# 用于诊断的文本集
DIAGNOSTIC_TEXTS = {
    "pure_chinese": [
        "你好",
        "你好，世界",
        "今天天气很好",
        "我是一个人工智能助手",
    ],
    "pure_english": [
        "Hello",
        "Hello, world",
        "The weather is nice today",
        "I am an artificial intelligence assistant",
    ],
    "mixed": [
        "Hello 你好",
        "世界 World",
        "AI 人工智能",
    ],
    "chinese_with_punctuation": [
        "你好！",
        "你好，世界。",
        "今天天气很好！对吧？",
    ],
    "numbers_and_symbols": [
        "2026年4月2号",
        "价格是¥99.99",
        "电话：13800138000",
    ],
}


def create_vibevoice_config() -> AppConfig:
    """创建 VibeVoice 专用配置"""
    return AppConfig(
        gemini_api_key="test",
        qwen_asr_base_url="http://test",
        fish_tts_base_url="http://test",
        mlx_tts_model_type="vibevoice",
        mlx_tts_vibevoice_model="mlx-community/VibeVoice-Realtime-0.5B-4bit",
        mlx_tts_kokoro_model="mlx-community/Kokoro-82M-4bit",
        mlx_tts_qwen3_model="mlx-community/Qwen3-TTS-12Hz-0.6B-Base-4bit",
        mlx_tts_language="zh",  # 明确设置中文
        mlx_tts_voice=None,
        mlx_tts_speed=1.0,
    )


async def diagnose_text_synthesis(
    text: str,
    text_category: str,
    output_dir: Path,
) -> dict:
    """诊断单个文本的合成
    
    Returns:
        诊断结果
    """
    result = {
        "text": text,
        "category": text_category,
        "success": False,
        "duration_ms": 0,
        "file_size": 0,
        "audio_file": None,
        "error": None,
    }
    
    try:
        config = create_vibevoice_config()
        adapter = MLXQwenTTSAdapter(
            model=config.mlx_tts_vibevoice_model,
            lang_code=config.mlx_tts_language,
            voice=config.mlx_tts_voice,
            speed=config.mlx_tts_speed,
        )
        
        logger.info(f"\n{'='*70}")
        logger.info(f"测试文本: {text[:50]}")
        logger.info(f"分类: {text_category}")
        logger.info(f"{'='*70}")
        
        start = time.perf_counter()
        audio_bytes = await adapter.synthesize(text)
        duration_ms = int((time.perf_counter() - start) * 1000)
        
        result["success"] = True
        result["duration_ms"] = duration_ms
        result["file_size"] = len(audio_bytes)
        
        # 保存音频
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_text = "".join(c if c.isalnum() or c in "_-" else "_" for c in text[:20])
        audio_file = output_dir / f"vibevoice_{text_category}_{safe_text}_{int(time.time())}.wav"
        
        with wave.open(str(audio_file), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(adapter._model.sample_rate)
            wav_file.writeframes(audio_bytes)
        
        result["audio_file"] = str(audio_file)
        
        logger.info(f"✓ 合成成功")
        logger.info(f"  耗时: {duration_ms}ms")
        logger.info(f"  大小: {len(audio_bytes)/1024:.1f}KB")
        logger.info(f"  采样率: {adapter._model.sample_rate}Hz")
        logger.info(f"  文件: {audio_file.name}")
        
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"✗ 合成失败: {e}", exc_info=True)
    
    return result


async def run_vibevoice_diagnosis() -> None:
    """运行完整的 VibeVoice 诊断"""
    
    output_dir = Path(__file__).parent.parent.parent / "tests" / "output" / "vibevoice_diagnosis"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n" + "="*70)
    print("VibeVoice 中文语言检测诊断")
    print("="*70)
    print(f"输出目录: {output_dir}")
    print("\n注意: 请手动播放生成的音频文件，检查：")
    print("  1. 发音是否是中文？")
    print("  2. 不同输入文本的发音有何区别？")
    print("  3. 是否有语言混淆的情况？")
    print("\n" + "="*70 + "\n")
    
    all_results = {}
    
    for category, texts in DIAGNOSTIC_TEXTS.items():
        logger.info(f"\n开始测试分类: {category}")
        all_results[category] = []
        
        for text in texts:
            result = await diagnose_text_synthesis(
                text=text,
                text_category=category,
                output_dir=output_dir,
            )
            all_results[category].append(result)
    
    # 打印诊断总结
    print("\n" + "="*70)
    print("诊断总结")
    print("="*70)
    
    for category, results in all_results.items():
        print(f"\n{category.upper()}:")
        successful = sum(1 for r in results if r["success"])
        print(f"  成功: {successful}/{len(results)}")
        
        for result in results:
            status = "✓" if result["success"] else "✗"
            text_preview = result["text"][:30]
            if result["success"]:
                print(f"  {status} {text_preview:<30} ({result['duration_ms']}ms)")
            else:
                print(f"  {status} {text_preview:<30} 错误: {result['error']}")
    
    print("\n" + "="*70)
    print(f"所有音频文件已保存到: {output_dir}")
    print("请逐一播放并检查输出语言是否正确")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(run_vibevoice_diagnosis())
