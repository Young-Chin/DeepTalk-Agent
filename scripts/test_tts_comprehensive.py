"""TTS 模型综合测试套件

包含离线测试用例，验证：
1. 模型基础功能
2. 多语言支持
3. 性能指标（延迟、质量）
4. 错误处理

使用方法:
    # 测试所有模型
    python3 -m app.tests.test_tts_comprehensive --all
    
    # 测试特定模型
    python3 -m app.tests.test_tts_comprehensive --model qwen3
    
    # 详细诊断
    python3 -m app.tests.test_tts_comprehensive --model vibevoice --diagnose
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import time
import wave
from dataclasses import dataclass, asdict
from pathlib import Path

from app.config import AppConfig
from app.tts.qwen_adapter import MLXQwenTTSAdapter


# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@dataclass
class TestCase:
    """测试用例"""
    name: str
    text: str
    lang: str
    description: str


@dataclass
class TestResult:
    """测试结果"""
    model_type: str
    test_case_name: str
    success: bool
    error: str | None = None
    duration_ms: int = 0
    file_size: int = 0
    sample_rate: int = 0
    output_file: str | None = None
    notes: str | None = None


# 测试用例集合
TEST_CASES = {
    "chinese": [
        TestCase(
            name="short_chinese",
            text="你好",
            lang="zh",
            description="短中文文本（2个字）"
        ),
        TestCase(
            name="medium_chinese",
            text="你好，欢迎参加这次访谈",
            lang="zh",
            description="中等中文文本（12个字）"
        ),
        TestCase(
            name="long_chinese",
            text="你好，欢迎参加这次访谈！我是主持人，很高兴能和你交流。今天我们来聊聊你的工作和经历。",
            lang="zh",
            description="长中文文本（40个字）"
        ),
        TestCase(
            name="chinese_with_punctuation",
            text="你好！我是AI助手。很高兴认识你。今天天气很好，对吧？",
            lang="zh",
            description="含标点的中文文本"
        ),
    ],
    "english": [
        TestCase(
            name="short_english",
            text="Hello",
            lang="en",
            description="短英文文本"
        ),
        TestCase(
            name="medium_english",
            text="Welcome to this interview. I'm the host.",
            lang="en",
            description="中等英文文本"
        ),
    ],
    "mixed": [
        TestCase(
            name="mixed_languages",
            text="你好 Hello 世界 World",
            lang="zh",
            description="混合中英文（测试语言检测）"
        ),
    ],
}


def create_test_config(model_type: str) -> AppConfig:
    """创建测试配置"""
    model_map = {
        "vibevoice": "mlx-community/VibeVoice-Realtime-0.5B-4bit",
        "kokoro": "mlx-community/Kokoro-82M-4bit",
        "qwen3": "mlx-community/Qwen3-TTS-12Hz-0.6B-Base-4bit",
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


async def run_test_case(
    model_type: str,
    test_case: TestCase,
    output_dir: Path | None = None,
    save_audio: bool = True,
    diagnose: bool = False,
) -> TestResult:
    """运行单个测试用例
    
    Args:
        model_type: 模型类型 (vibevoice, kokoro, qwen3)
        test_case: 测试用例
        output_dir: 输出目录
        save_audio: 是否保存音频文件
        diagnose: 是否打印诊断信息
    
    Returns:
        测试结果
    """
    result = TestResult(
        model_type=model_type,
        test_case_name=test_case.name,
        success=False,
    )
    
    try:
        # 创建配置和适配器
        config = create_test_config(model_type)
        model_path = getattr(config, f"mlx_tts_{model_type}_model")
        
        adapter = MLXQwenTTSAdapter(
            model=model_path,
            lang_code=test_case.lang,
            voice=None,
            speed=1.0,
        )
        
        # 合成音频
        start = time.perf_counter()
        audio_bytes = await adapter.synthesize(test_case.text)
        duration_ms = int((time.perf_counter() - start) * 1000)
        
        result.success = True
        result.duration_ms = duration_ms
        result.file_size = len(audio_bytes)
        result.sample_rate = adapter._model.sample_rate
        
        # 保存音频文件
        if save_audio and output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / f"{model_type}_{test_case.name}.wav"
            
            with wave.open(str(output_file), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(adapter._model.sample_rate)
                wav_file.writeframes(audio_bytes)
            
            result.output_file = str(output_file)
        
        # 诊断信息
        if diagnose:
            logger.info(f"✓ {model_type} 成功")
            logger.info(f"  文本: {test_case.text}")
            logger.info(f"  耗时: {duration_ms}ms")
            logger.info(f"  大小: {len(audio_bytes)/1024:.1f}KB")
            logger.info(f"  采样率: {adapter._model.sample_rate}Hz")
        
    except Exception as e:
        result.error = str(e)
        if diagnose:
            logger.error(f"✗ {model_type} 失败: {e}", exc_info=True)
    
    return result


async def test_model_with_language_variants(
    model_type: str,
    output_dir: Path | None = None,
    diagnose: bool = False,
) -> dict:
    """用多语言测试用例测试单个模型
    
    Returns:
        {language: [TestResult, ...]}
    """
    results = {}
    
    for lang_group, test_cases in TEST_CASES.items():
        results[lang_group] = []
        
        for test_case in test_cases:
            result = await run_test_case(
                model_type=model_type,
                test_case=test_case,
                output_dir=output_dir,
                diagnose=diagnose,
            )
            results[lang_group].append(result)
    
    return results


def print_test_report(all_results: dict[str, dict]) -> None:
    """打印测试报告"""
    print("\n" + "="*100)
    print("TTS 模型综合测试报告")
    print("="*100)
    
    for model_type, lang_results in all_results.items():
        print(f"\n{'模型':<15} {model_type}")
        print("-"*100)
        
        for lang_group, test_results in lang_results.items():
            print(f"\n  {lang_group.upper()} 测试组:")
            print(f"  {'测试名称':<25} {'状态':<8} {'耗时(ms)':<12} {'大小(KB)':<12} {'采样率'}")
            
            for result in test_results:
                status = "✓ 成功" if result.success else "✗ 失败"
                duration = f"{result.duration_ms}" if result.success else "-"
                size = f"{result.file_size/1024:.1f}" if result.success else "-"
                sample_rate = f"{result.sample_rate}" if result.success else "-"
                
                print(
                    f"  {result.test_case_name:<25} {status:<8} "
                    f"{duration:<12} {size:<12} {sample_rate}"
                )
                
                if result.error:
                    print(f"    错误: {result.error}")


async def run_comprehensive_test(
    models: list[str],
    output_dir: Path | None = None,
    diagnose: bool = False,
    save_report: bool = False,
) -> dict:
    """运行完整测试套件"""
    
    if not output_dir:
        output_dir = Path(__file__).parent.parent.parent / "tests" / "output"
    
    all_results = {}
    
    for model_type in models:
        print(f"\n开始测试模型: {model_type}")
        print("="*80)
        
        results = await test_model_with_language_variants(
            model_type=model_type,
            output_dir=output_dir,
            diagnose=diagnose,
        )
        all_results[model_type] = results
    
    # 打印报告
    print_test_report(all_results)
    
    # 保存报告为JSON
    if save_report:
        report_file = output_dir / f"test_report_{int(time.time())}.json"
        report_data = {
            model_type: {
                lang_group: [asdict(r) for r in results]
                for lang_group, results in lang_results.items()
            }
            for model_type, lang_results in all_results.items()
        }
        
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n报告已保存: {report_file}")
    
    return all_results


def main():
    parser = argparse.ArgumentParser(description="TTS 模型综合测试套件")
    parser.add_argument(
        "--model",
        type=str,
        choices=["vibevoice", "kokoro", "qwen3"],
        help="测试特定模型"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="测试所有模型"
    )
    parser.add_argument(
        "--diagnose",
        action="store_true",
        help="打印详细诊断信息"
    )
    parser.add_argument(
        "--save-report",
        action="store_true",
        help="保存测试报告为JSON"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="输出目录"
    )
    
    args = parser.parse_args()
    
    # 确定要测试的模型
    if args.all:
        models = ["vibevoice", "kokoro", "qwen3"]
    elif args.model:
        models = [args.model]
    else:
        models = ["qwen3"]  # 默认测试 qwen3
    
    output_dir = Path(args.output_dir) if args.output_dir else None
    
    # 运行测试
    asyncio.run(run_comprehensive_test(
        models=models,
        output_dir=output_dir,
        diagnose=args.diagnose,
        save_report=args.save_report,
    ))


if __name__ == "__main__":
    main()
