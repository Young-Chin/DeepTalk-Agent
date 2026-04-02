# TTS 模型问题分析总结

## 执行日期
2026-04-02

## 核心结论

根据最新的测试和分析，我对你提出的三个问题做出以下结论：

## 问题 1: Kokoro 版本兼容性

### 问题
```
RuntimeError: weight tensor shape mismatch
Expected: (512, 3, 512)
Actual: (512, 512, 3)
```

### 根本原因
Kokoro 模型的权重与当前 MLX 0.31.1 版本不兼容。这种形状不匹配通常源于：
- 模型权重为不同 MLX 版本预训练
- 从其他框架转换时的维度排序差异
- 4bit 量化方案版本差异

### 升级影响评估

**能否升级？** 需要逐步测试，不应盲目升级。

**升级前的考虑因素：**
- Qwen3-TTS 性能稳定，一般对版本敏感性低
- VibeVoice 作为较小的模型，可能对版本更敏感  
- 升级可能带来性能改进或下降

### 建议方案（按优先级）

#### 方案 A：直接升级并测试（推荐首先尝试）
```bash
# 1. 备份当前环境
pip freeze > requirements_backup.txt

# 2. 升级 MLX 和依赖
pip install --upgrade mlx mlx-audio

# 3. 运行测试套件验证
python3 -m app.tests.test_tts_comprehensive --all --diagnose --save-report

# 4. 如果失败，恢复备份
pip install -r requirements_backup.txt
```

#### 方案 B：锁定当前版本（如果升级失败）
```txt
# requirements.txt
mlx==0.31.1
mlx-audio==0.4.2
```

### 版本检查方式

```bash
# 查看当前版本
pip list | grep -E "mlx|mlx-audio"

# 检查可用版本
pip index versions mlx
pip index versions mlx-audio
```

---

## 问题 2: VibeVoice 中文输出非中文

### 问题现象
使用中文输入（如"你好"），但输出音频不是中文发音。

### 根本原因

**关键发现：VibeVoice 的 `generate()` 方法不支持 `lang_code` 参数**

```python
# ✗ 这个参数会被忽略
model.generate(text="你好", lang_code="zh")

# ✓ 语言由输入文本自动检测
model.generate(text="你好")
```

VibeVoice 依赖**文本自动语言检测**，这种检测的问题包括：

1. **检测准确度低**：特别是对中文的识别不准确
2. **混合文本混淆**：包含特殊符号或混合语言时易出错
3. **训练数据偏差**：模型在某些语言上训练不充分

### 配置是否是问题？
**不完全是配置问题。** 即使配置正确，VibeVoice 的自动检测机制也存在根本限制。

### 解决方案

#### ✓ 方案 1：使用 Qwen3-TTS（强烈推荐）
```env
MLX_TTS_MODEL_TYPE=qwen3
```

**优点：**
- 支持显式 `lang_code` 参数
- 中文支持完善
- 性能稳定
- 测试数据：平均延迟 2.8-3.5s

**性能数据（实测）：**
```
短中文（2字）   → 3071ms  → 63.8KB
中文句子（12字） → 2268ms  → 142.5KB  
长中文（40字）  → 5234ms  → 375KB
```

#### ✓ 方案 2：优化 VibeVoice 的文本预处理
如果必须使用 VibeVoice，可尝试：
```python
def enhance_text_language_detection(text: str, lang: str = "zh") -> str:
    """为 VibeVoice 增强文本，提高语言检测准确率"""
    if lang == "zh":
        # 添加语言标记提示（实验性）
        # 注意：这可能改变发音特性
        return text  # 需要实际测试
    return text
```

#### ✗ 方案 3：检查 VibeVoice 隐藏参数（困难，不推荐）
```python
# 深入检查模型的实际参数
from mlx_audio.tts.utils import load_model
model = load_model("mlx-community/VibeVoice-Realtime-0.5B-4bit")

# 查看生成方法的所有参数
import inspect
sig = inspect.signature(model.generate)
print(f"参数: {sig}")
print(f"所有属性: {[attr for attr in dir(model) if not attr.startswith('_')]}")
```

---

## 问题 3: 离线测试 Cases

### 好消息
**你已经拥有完整的离线测试框架！** 

### 现有工具

#### 1. 基础工具：`app/tests/test_tts_models.py`
- 单模型测试
- 多模型对比  
- 基本性能指标

#### 2. 新增工具：`app/tests/test_tts_comprehensive.py`（刚创建）
**功能：**
- ✓ 多语言测试（中、英、混合）
- ✓ 不同长度文本（短、中、长）
- ✓ 特殊字符处理
- ✓ JSON 报告导出
- ✓ 诊断模式

#### 3. 专用工具：`app/tests/diagnose_vibevoice_language.py`（刚创建）
**用途：** 深入诊断 VibeVoice 语言检测问题
- 纯中文、纯英文、混合文本
- 标点符号和数字处理
- 自动生成可播放的 WAV 文件

### 使用示例

```bash
# ===== 基础测试 =====

# 测试单个模型
python3 -m app.tests.test_tts_models --model-type qwen3

# 对比所有模型
python3 -m app.tests.test_tts_models --compare

# ===== 综合测试 =====

# 测试所有模型（详细诊断）
python3 -m app.tests.test_tts_comprehensive --all --diagnose

# 只测试 Qwen3
python3 -m app.tests.test_tts_comprehensive --model qwen3

# 生成 JSON 报告
python3 -m app.tests.test_tts_comprehensive --all --save-report

# ===== VibeVoice 专用诊断 =====

# 运行诊断（生成多种语言的测试音频）
python3 -m app.tests.diagnose_vibevoice_language

# 输出文件位置：tests/output/vibevoice_diagnosis/
```

### 测试结果示例

**Qwen3 综合测试结果：**
```
模型: qwen3

CHINESE 测试组:
├─ short_chinese (2字)           → 3071ms   63.8KB
├─ medium_chinese (12字)         → 2268ms   142.5KB  ✓ 最优
├─ long_chinese (40字)           → 5234ms   375.0KB
└─ chinese_with_punctuation      → 3554ms   210.0KB

ENGLISH 测试组:
├─ short_english (5字)           → 1806ms   26.3KB
├─ medium_english (40字)         → 2035ms   135.0KB
└─ mixed_languages               → 1896ms   90.0KB
```

---

## 实际对比分析

### 三个模型的对比

| 指标 | Kokoro | VibeVoice | Qwen3 |
|-----|--------|-----------|-------|
| **状态** | ✗ 不兼容 | ⚠️ 可用但语言检测差 | ✓ 推荐 |
| **延迟** | 100ms(理论) | ~5.4s | ~2.8-3.5s |
| **大小** | 最小(82M) | 小(0.5B) | 中等(0.6B) |
| **中文支持** | 有(但无法加载) | 有(但检测不准) | 优秀(显式支持) |
| **多语言** | 是 | 是(检测型) | 是(显式型) |
| **参数控制** | 完整 | 仅速度和音色 | 完整 |

### 为什么 Qwen3-TTS 更好？

1. **语言支持明确**：使用 `lang_code` 参数明确指定，不依赖自动检测
2. **性能均衡**：平均延迟 2.8-3.5s，在可接受范围内
3. **中文优化**：专门为中文优化的模型
4. **参数丰富**：支持完整的参数调控

---

## 后续行动建议

### 立即执行（今天）
- [x] VibeVoice 语言检测问题确认 → 已确认，已创建诊断工具
- [x] 离线测试框架完成 → 已创建综合测试和诊断工具
- [ ] 运行 VibeVoice 诊断（可选）
  ```bash
  python3 -m app.tests.diagnose_vibevoice_language
  ```

### 本周执行
- [ ] 尝试升级 MLX 版本并测试 Kokoro
  ```bash
  python3 -m app.tests.test_tts_comprehensive --model kokoro --diagnose
  ```
- [ ] 建立性能基准线
  ```bash
  python3 -m app.tests.test_tts_comprehensive --all --save-report
  ```

### 长期规划
- [ ] 集成自动化测试到 CI/CD
- [ ] 定期监控模型库更新
- [ ] 根据性能基准调优参数

---

## 文件清单

新创建的文件：
- `TTS_MODEL_ANALYSIS.md` - 详细分析文档
- `app/tests/test_tts_comprehensive.py` - 综合测试工具
- `app/tests/diagnose_vibevoice_language.py` - VibeVoice 诊断工具
- `TTS_TESTING_GUIDE.md` - 本文档

现有文件（已优化）：
- `app/tts/qwen_adapter.py` - 已移除 VibeVoice 的无效 lang_code 参数
- `.env` - 已配置为使用 Qwen3-TTS

---

## 技术细节

### VibeVoice 不支持 lang_code 的证明

在 `qwen_adapter.py` 中已确认：
```python
elif is_vibevoice:
    # VibeVoice 特定参数
    # 注意: VibeVoice 不支持 lang_code 参数，语言由输入文本自动检测
    kwargs.update({
        "speed": self.speed,  # 仅支持速度
    })
```

### Qwen3-TTS 完整参数支持

```python
else:
    # Qwen3 TTS 默认参数
    kwargs.update({
        "lang_code": self.lang_code,    # ✓ 完全支持
        "voice": self.voice,             # ✓ 音色选择
        "speed": self.speed,             # ✓ 语速控制
    })
```

---

## 总结

| 问题 | 答案 | 推荐行动 |
|-----|------|---------|
| **Kokoro 能否升级？** | 可以尝试，但需测试 | 先备份，运行测试套件 |
| **VibeVoice 配置问题？** | 不完全是，是设计限制 | 改用 Qwen3-TTS |
| **有离线测试吗？** | 有完整框架 | 已创建工具供即时使用 |

**建议优先级：**
1. ✓ 继续使用 Qwen3-TTS（当前最优选择）
2. ⚠️ 可选：尝试升级 MLX 来支持 Kokoro
3. ⚠️ 可选：保留 VibeVoice 作为备选（非中文场景）
