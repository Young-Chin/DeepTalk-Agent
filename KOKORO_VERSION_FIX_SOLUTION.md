# Kokoro TTS 版本兼容性解决方案

## 问题总结

Kokoro TTS 模型在旧版本的 `mlx-audio` 中会出现权重形状不匹配错误：
```
ValueError: Expected shape (512, 3, 1) but received shape (512, 1, 3) for parameter predictor.F0.1.pool.weight_v
```

## 根本原因

- **mlx-audio 0.2.10 及更早版本**：Kokoro 权重处理有兼容性问题，导致张量形状错误
- **mlx-audio 0.4.2+**：已修复权重转换问题，Kokoro 可以正常工作

## 解决方案

### 方案 1：完整升级（推荐）

```bash
# 升级 mlx-audio 到最新版本
pip3 install --upgrade mlx-audio

# 降级 NumPy 到 1.x（处理兼容性问题）
pip3 install "numpy<2" scipy --upgrade
```

验证版本：
```bash
pip3 show mlx-audio | grep Version  # 应显示 0.4.2+
pip3 show numpy | grep Version       # 应显示 1.26.x
```

### 方案 2：使用专用虚拟环境（如你的 .kokoro）

如果你已经有一个配置好的虚拟环境（例如 `.kokoro`），可以直接使用它：

```bash
source .kokoro/bin/activate
mlx_audio.tts.generate --model mlx-community/Kokoro-82M-bf16 --text "Hello!" --play
```

## 环境版本矩阵

### ✅ 工作的配置
| MLX | mlx-audio | NumPy | Python | Kokoro | VibeVoice | 状态 |
|-----|-----------|-------|--------|--------|-----------|------|
| 0.31.1 | 0.4.2 | 1.26.4 | 3.10.7 | ✅ | ✅ | 完全正常 |

### ⚠️ 部分工作的配置
| MLX | mlx-audio | NumPy | Python | Kokoro | VibeVoice | 说明 |
|-----|-----------|-------|--------|--------|-----------|------|
| 0.31.1 | 0.4.2 | 2.2.6 | 3.10.7 | ✅ bf16 | ❌ | NumPy 2.x 导致 VibeVoice numpy 兼容性问题 |

### ❌ 不工作的配置
| MLX | mlx-audio | NumPy | Python | 错误 |
|-----|-----------|-------|--------|------|
| 0.31.1 | 0.2.10 | 任何 | 3.10.7 | Kokoro 权重形状不匹配 |

## 验证修复

升级后，运行以下命令验证 Kokoro 是否正常工作：

```python
from mlx_audio.tts.utils import load_model

model = load_model("mlx-community/Kokoro-82M-bf16")
print("✅ Kokoro loaded successfully!")

# 测试完整的生成管道
audio_gen = model.generate(
    text="Hello world, this is a test.",
    lang_code="a",
    speed=1.0
)
print("✅ Audio generation successful!")
```

## Kokoro 模型变体

所有以下变体都支持：

| 模型 | 参数量 | 推荐用途 |
|------|--------|---------|
| `mlx-community/Kokoro-82M-bf16` | 82M | 通用（推荐） |
| `mlx-community/Kokoro-82M` | 82M | 量化版本 |
| 其他变体 | - | 需要相同的 mlx-audio 版本 |

## 常见问题

### Q: PR #423 是什么？
A: GitHub PR #423 针对 mlx-audio 库的权重形状检查进行了改进。这个 PR 的逻辑已经在 mlx-audio 0.4.2+ 中实现，不需要手动应用。

### Q: 我应该降级还是升级？
A: **升级到 mlx-audio 0.4.2+**。这是官方的修复，已经通过测试验证。

### Q: 其他 TTS 模型受影响吗？
A: 主要影响 Kokoro。VibeVoice 和 Qwen3-TTS 在两个版本中都可以工作。

## 总结

| 任务 | 状态 |
|------|------|
| 修复 Kokoro 加载失败 | ✅ 已解决（升级 mlx-audio 到 0.4.2+） |
| 修复 VibeVoice 中文输出 | ✅ 已解决（使用 Qwen3-TTS） |
| CosyVoice3 支持 | ✅ 需要 mlx-audio-plus |

## 实际测试结果

2026-04-03 环境测试结果：

```
✅ Kokoro-82M-bf16 - 完全正常
✅ VibeVoice-Realtime-0.5B-4bit - 完全正常
✅ Qwen3-TTS-12Hz-0.6B-Base-4bit - 完全正常
✅ 应用启动成功 - 所有模型预加载正常
```

**建议的后续步骤：**

1. 如果你还没有升级，运行以下命令：
   ```bash
   pip3 install --upgrade mlx-audio
   pip3 install "numpy<2" scipy --upgrade
   ```

2. 验证所有 TTS 模型工作：
   ```bash
   python3 -c "from mlx_audio.tts.utils import load_model; load_model('mlx-community/Kokoro-82M-bf16'); print('✅ Kokoro works!')"
   ```

3. 如果需要使用 Kokoro 作为默认模型，在 `.env` 中更改：
   ```
   MLX_TTS_MODEL_TYPE=kokoro
   ```

4. 启动应用测试：
   ```bash
   python3 -m app.main
   ```
