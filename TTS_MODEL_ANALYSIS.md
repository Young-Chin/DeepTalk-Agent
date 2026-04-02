# TTS 模型版本和语言问题分析

## 概述

本文档深入分析了三个关键问题：
1. Kokoro 模型版本兼容性
2. VibeVoice 中文识别问题
3. 离线测试框架

## 问题 1: Kokoro MLX 版本兼容性

### 问题现象
```
RuntimeError: weight tensor shape mismatch
Expected: (512, 3, 512)
Actual: (512, 512, 3)
```

### 根本原因

Kokoro 模型的权重文件与当前 MLX 0.31.1 版本不兼容。这种形状不匹配通常发生在以下情况：

1. **模型和框架版本不匹配**：模型可能是为了不同版本的 MLX 预训练的
2. **权重转换不完整**：从其他框架（如 PyTorch）到 MLX 的转换过程中可能出现问题
3. **量化方式差异**：4bit 量化方案在不同版本间可能有变化

### 检查 MLX 版本兼容性的步骤

```bash
# 1. 查看当前版本
pip list | grep -i mlx

# 2. 检查 MLX 更新日志
pip index versions mlx

# 3. 检查 mlx-audio 版本
pip list | grep mlx-audio
```

### 升级测试方案

```bash
# 备份当前环境
pip freeze > requirements_backup.txt

# 升级 MLX 到最新版本
pip install --upgrade mlx

# 升级 mlx-audio
pip install --upgrade mlx-audio

# 运行 Kokoro 测试
python3 -m app.tests.test_tts_comprehensive --model kokoro --diagnose
```

### 升级对其他模型的影响

升级 MLX 版本前需要考虑：

- **Qwen3-TTS**: 通常兼容性较好，因为是最新主流模型
- **VibeVoice**: 需要测试，较小的模型可能对版本更敏感

### 降级/锁定版本的方案

如果升级导致问题，可以在 `requirements.txt` 中锁定版本：

```
mlx==0.31.1
mlx-audio==0.4.2
```

## 问题 2: VibeVoice 中文输出非中文

### 问题现象

使用中文输入文本，但输出音频听起来不是中文发音。

### 根本原因分析

VibeVoice 的 `generate()` 方法**不支持 `lang_code` 参数**，语言**完全由输入文本自动检测**：

```python
# ✗ 错误（会被忽略）
model.generate(text="你好", lang_code="zh")

# ✓ 正确（语言由文本自动检测）
model.generate(text="你好")
```

### 自动语言检测的问题

1. **检测不准确**：混合语言或特殊格式可能导致误检测
2. **模型训练偏好**：VibeVoice 在某些语言上的训练数据更充分
3. **文本预处理问题**：文本编码或格式可能影响检测

### 诊断步骤

已创建专用诊断工具：

```bash
# 运行 VibeVoice 诊断
python3 -m app.tests.diagnose_vibevoice_language

# 这会生成多个 WAV 文件：
# - pure_chinese 类别（纯中文文本）
# - pure_english 类别（纯英文文本）
# - mixed 类别（混合文本）
# - 带标点符号的文本
# - 包含数字的文本

# 手动播放这些文件，检查发音是否正确
```

### 解决方案

#### 1. **强制使用 Qwen3-TTS**（推荐）
```env
MLX_TTS_MODEL_TYPE=qwen3
```
- ✓ 支持 `lang_code` 参数，显式控制语言
- ✓ 中文支持更完善
- ✓ 更稳定可靠

#### 2. **改进 VibeVoice 的文本预处理**
```python
# 方案：添加语言标记或强制格式
def prepare_text_for_vibevoice(text: str, lang: str = "zh") -> str:
    """为 VibeVoice 预处理文本，提高语言检测准确性"""
    if lang == "zh":
        # 对于中文，可以添加一些提示性文本
        # 但这可能改变发音，需要测试
        pass
    return text
```

#### 3. **寻找 VibeVoice 的语言标记参数**
```python
# 检查 VibeVoice 模型的实际参数
from mlx_audio.tts.utils import load_model
model = load_model("mlx-community/VibeVoice-Realtime-0.5B-4bit")
import inspect
print(inspect.signature(model.generate))

# 查看是否有隐藏的语言相关参数
print(dir(model))
```

## 问题 3: 离线测试框架

### 现有测试工具

#### 1. **基础测试工具** (`test_tts_models.py`)
- 单个模型测试
- 模型对比测试
- 基本性能指标

#### 2. **新增综合测试工具** (`test_tts_comprehensive.py`)
- ✓ 多语言测试用例（中文、英文、混合）
- ✓ 不同长度的文本（短、中、长）
- ✓ 标点符号和特殊字符
- ✓ JSON 报告导出
- ✓ 详细诊断模式

#### 3. **VibeVoice 专用诊断** (`diagnose_vibevoice_language.py`)
- ✓ 纯中文文本测试
- ✓ 纯英文文本测试
- ✓ 混合语言测试
- ✓ 标点符号和数字处理
- ✓ 自动生成可播放的 WAV 文件

### 使用示例

```bash
# 测试所有模型（详细输出）
python3 -m app.tests.test_tts_comprehensive --all --diagnose

# 只测试 Qwen3
python3 -m app.tests.test_tts_comprehensive --model qwen3

# 测试并保存 JSON 报告
python3 -m app.tests.test_tts_comprehensive --all --save-report

# VibeVoice 专用诊断
python3 -m app.tests.diagnose_vibevoice_language

# 基础测试工具
python3 -m app.tests.test_tts_models --model-type qwen3
python3 -m app.tests.test_tts_models --compare  # 对比所有模型
```

## 测试结果解读

### 性能指标

| 指标 | 含义 | 正常范围 |
|-----|------|---------|
| 耗时 (ms) | 从合成请求到输出音频的时间 | Qwen3: 2000-5000ms |
| 大小 (KB) | 输出音频文件的大小 | 长度依赖，通常 50-300KB |
| 采样率 (Hz) | 音频采样率 | 24000Hz (Qwen3) |

### 常见问题和对应操作

| 问题 | 原因 | 解决方案 |
|-----|------|---------|
| RuntimeError: shape mismatch | MLX 版本不兼容 | 升级/锁定 MLX 版本 |
| ModuleNotFoundError: mlx_audio | 缺少依赖 | pip install mlx-audio |
| 输出音频非目标语言 | VibeVoice 语言检测失败 | 切换到 Qwen3 或优化文本 |
| 超时 (>10000ms) | 模型加载缓慢或硬件不足 | 检查磁盘空间和系统资源 |

## 推荐配置

基于当前分析，推荐使用以下配置：

### `.env` 推荐设置

```env
# TTS 模型选择
TTS_BACKEND=mlx_qwen3
MLX_TTS_MODEL_TYPE=qwen3

# Qwen3 配置（推荐）
MLX_TTS_QWEN3_MODEL=mlx-community/Qwen3-TTS-12Hz-0.6B-Base-4bit

# 备用模型配置（如果需要）
MLX_TTS_VIBEVOICE_MODEL=mlx-community/VibeVoice-Realtime-0.5B-4bit
MLX_TTS_KOKORO_MODEL=mlx-community/Kokoro-82M-4bit

# 语言和语速
MLX_TTS_LANGUAGE=zh
MLX_TTS_SPEED=1.0
```

## 后续工作

### 短期（立即）
- [ ] 运行 VibeVoice 诊断，确认语言检测问题
- [ ] 运行综合测试，生成基准数据
- [ ] 记录测试结果

### 中期（本周）
- [ ] 尝试升级 MLX 版本，测试 Kokoro 兼容性
- [ ] 如果升级成功，评估性能差异
- [ ] 如果升级失败，考虑模型转换方案

### 长期（本月）
- [ ] 集成自动化测试到 CI/CD
- [ ] 建立性能基准
- [ ] 定期监控模型更新
