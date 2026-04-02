"""TTS 模型测试验证框架

用于测试不同 TTS 模型的合成效果，验证配置是否正确。

使用方法:
    python3 -m app.tests.test_tts_models --model-type kokoro
    python3 -m app.tests.test_tts_models --model-type vibevoice
    python3 -m app.tests.test_tts_models --model-type qwen3
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import wave
from pathlib import Path

from app.config import AppConfig
from app.tts.qwen_adapter import MLXQwenTTSAdapter


# 测试文本
TEST_TEXTS = {
    "short": "你好",
    "medium": "你好，欢迎参加这次访谈",
    "long": "你好，欢迎参加这次访谈！我是主持人，很高兴能和你交流。今天我们来聊聊你的工作和经历。",
}


def create_test_config(model_type: str) -> AppConfig:
    """创建测试配置"""
    model_map = {
        "vibevoice": "modelscope/VibeVoice-Realtime-0.5B-4bit",
        "kokoro": "modelscope/Kokoro-82M-4bit",
        "qwen3": "modelscope/Qwen3-TTS-12Hz-0.6B-Base-4bit",
    }
    
    return AppConfig(
        gemini_api_key="test",
        qwen_asr_base_url="http://test",
        fish_tts_base_url="http://test",
        mlx_tts_model_type=model_type,
        mlx_tts_vibevoice_model=model_map["vibevoice"],
        mlx_tts_kokoro_model=model_map["kokoro"],
        mlx_tts_qwen3_model=model_map["qwen3"],
        mlx_tts_language="zh",
        mlx_tts_voice=None,
        mlx_tts_speed=1.0,
    )


async def test_tts_synthesis(
    model_type: str,
    text: str = TEST_TEXTS["medium"],
    output_file: str | None = None,
    verbose: bool = False,
) -> dict:
    """测试 TTS 合成功能
    
    Returns:
        测试结果字典，包含 success、duration_ms、file_size 等
    """
    result = {
        "model_type": model_type,
        "success": False,
        "error": None,
        "text_length": len(text),
        "duration_ms": 0,
        "file_size": 0,
        "output_file": None,
    }
    
    print(f"\n{'='*60}")
    print(f"测试 TTS 模型：{model_type}")
    print(f"测试文本：{text[:50]}{'...' if len(text) > 50 else ''}")
    print(f"{'='*60}")
    
    try:
        # 创建配置和适配器
        config = create_test_config(model_type)
        model_path = getattr(config, f"mlx_tts_{model_type}_model")
        
        print(f"模型路径：{model_path}")
        print("正在加载模型...")
        
        adapter = MLXQwenTTSAdapter(
            model=model_path,
            lang_code=config.mlx_tts_language,
            voice=config.mlx_tts_voice,
            speed=config.mlx_tts_speed,
        )
        
        # 合成音频
        import time
        start = time.perf_counter()
        print("开始合成...")
        audio_bytes = await adapter.synthesize(text)
        duration_ms = int((time.perf_counter() - start) * 1000)
        
        result["success"] = True
        result["duration_ms"] = duration_ms
        result["file_size"] = len(audio_bytes)
        
        print(f"✓ 合成成功!")
        print(f"  - 耗时：{duration_ms}ms")
        print(f"  - 音频大小：{len(audio_bytes)/1024:.1f} KB")
        print(f"  - 采样率：{adapter._model.sample_rate} Hz")
        
        # 保存文件
        if output_file:
            output_path = Path(output_file)
        else:
            output_dir = Path(__file__).parent.parent.parent / "tests" / "output"
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / f"tts_test_{model_type}_{int(time.time())}.wav"
        
        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(adapter._model.sample_rate)
            wav_file.writeframes(audio_bytes)
        
        result["output_file"] = str(output_path)
        print(f"  - 输出文件：{output_path}")
        
        if verbose:
            print(f"\n详细参数:")
            print(f"  - 语言：{config.mlx_tts_language}")
            print(f"  - 语速：{config.mlx_tts_speed}")
            print(f"  - 音色：{config.mlx_tts_voice or '默认'}")
        
    except Exception as e:
        result["error"] = str(e)
        print(f"✗ 合成失败: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
    
    print(f"{'='*60}\n")
    return result


def compare_models(models: list[str], text: str = TEST_TEXTS["medium"]) -> None:
    """对比多个模型的性能"""
    results = []
    
    for model_type in models:
        result = asyncio.run(test_tts_synthesis(model_type, text))
        results.append(result)
    
    # 打印对比表格
    print("\n" + "="*80)
    print("模型性能对比")
    print("="*80)
    print(f"{'模型':<15} {'状态':<8} {'耗时 (ms)':<12} {'大小 (KB)':<12} {'输出文件'}")
    print("-"*80)
    
    for r in results:
        status = "✓ 成功" if r["success"] else f"✗ 失败"
        duration = f"{r['duration_ms']}" if r["success"] else "-"
        size = f"{r['file_size']/1024:.1f}" if r["success"] else "-"
        file_name = Path(r["output_file"]).name if r["output_file"] and r["success"] else "-"
        
        print(f"{r['model_type']:<15} {status:<8} {duration:<12} {size:<12} {file_name}")
    
    print("="*80)


def main():
    parser = argparse.ArgumentParser(description="TTS 模型测试工具")
    parser.add_argument(
        "--model-type",
        type=str,
        default="vibevoice",
        choices=["vibevoice", "kokoro", "qwen3"],
        help="TTS 模型类型"
    )
    parser.add_argument(
        "--text",
        type=str,
        default=TEST_TEXTS["medium"],
        help="测试文本"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="输出文件路径"
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="对比所有模型"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="显示详细信息"
    )
    
    args = parser.parse_args()
    
    if args.compare:
        compare_models(["vibevoice", "kokoro", "qwen3"], args.text)
    else:
        asyncio.run(test_tts_synthesis(
            args.model_type,
            args.text,
            args.output,
            args.verbose
        ))


if __name__ == "__main__":
    main()
