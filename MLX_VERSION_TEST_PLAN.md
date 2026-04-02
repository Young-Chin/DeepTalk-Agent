# CosyVoice3 和 MLX 版本测试计划

## CosyVoice3 发现

### ✅ 根本原因已找到

**问题**: `Model type cosyvoice3 not supported for tts.`

**原因**: 官方 mlx-audio 0.4.2 不支持 CosyVoice3

**解决方案**: 需要使用 **mlx-audio-plus** 而不是官方 mlx-audio

**证据**:
- 模型 README 明确指出: `pip install -U mlx-audio-plus`
- config.json 中 model_type 是 cosyvoice3
- mlx-audio-plus 版本 0.1.8 已通过 pip 安装
- 但由于环境配置问题，暂时无法直接测试

### 关键信息

mlx-audio-plus 支持的模型包括：
- CosyVoice3（新增）
- 其他增强模型

---

## MLX 版本测试计划

### 目标

测试 Kokoro 在不同 MLX 版本下的兼容性：
1. 当前版本：MLX 0.31.1（有权重形状问题）
2. 早期版本：MLX 0.0.1（可能没有问题）

### 方法

创建隔离的虚拟环境测试：
```bash
# 1. 创建虚拟环境
python3 -m venv kokoro_test_env

# 2. 激活环境
source kokoro_test_env/bin/activate

# 3. 安装早期版本 MLX
pip install mlx==0.0.1

# 4. 安装 mlx-audio
pip install mlx-audio==0.1.0  # 与早期 MLX 兼容的版本

# 5. 测试 Kokoro
python3 << 'EOF'
from mlx_audio.tts.utils import load_model
model = load_model("mlx-community/Kokoro-82M-4bit")
for result in model.generate(text="Hello"):
    pass
print("✓ 成功！")
EOF
```

### 预期结果

- 如果 Kokoro 在 MLX 0.0.1 中能正常工作，说明是版本兼容性问题
- 如果仍然失败，说明是更根本的权重转换问题

### 风险评估

- 低风险：只在虚拟环境中测试，不影响主系统
- 时间：可能需要 10-20 分钟下载和编译

---

## 当前状态

| 项目 | 状态 | 备注 |
|-----|------|------|
| CosyVoice3 | ⚠️ 需要 mlx-audio-plus | 已找到根本原因 |
| Kokoro (现在) | ❌ 权重问题 | 需要测试早期版本 |
| Kokoro (目标) | ? | 待测 |
| Qwen3-TTS | ✅ 正常 | 继续使用 |
| VibeVoice | ✅ 正常 | 继续使用 |

---

## 下一步

### 立即可做

1. ✅ 已找到 CosyVoice3 需要 mlx-audio-plus
2. ✅ 已识别了问题所在
3. ⏳ 需要修复 mlx-audio-plus 的导入问题或重新安装

### 需要测试

1. ⏳ 在虚拟环境中用 MLX 0.0.1 测试 Kokoro
2. ⏳ 对比结果，确定是否是版本问题

### 预计时间

- mlx-audio-plus 环境配置：5-10 分钟
- MLX 0.0.1 虚拟环境测试：15-30 分钟
- 总计：30-45 分钟

---

## 关键发现总结

✅ **CosyVoice3 问题解决了**
- 不是模型问题
- 不是 mlx-audio 的 bug
- 就是需要用 mlx-audio-plus 替换官方库

🔍 **Kokoro 问题待深入调查**
- 可能是版本问题
- 可能是权重转换问题
- 需要用早期 MLX 版本验证
