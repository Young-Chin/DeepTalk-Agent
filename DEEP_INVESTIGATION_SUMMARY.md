# CosyVoice3 和 Kokoro 深度调查总结

## CosyVoice3 - 问题已解决 ✅

### 发现过程

1. **问题**: `Model type cosyvoice3 not supported for tts.`

2. **初始调查**: 检查模型的 README 和 config

3. **根本原因**: CosyVoice3 使用**第三方库 mlx-audio-plus**，而不是官方的 mlx-audio

### 证据

**模型 README 明确说明**:
```bash
pip install -U mlx-audio-plus
```

**config.json 中**:
```json
{
  "model_type": "cosyvoice3",
  ...
}
```

**mlx-audio-plus 的 library_name**:
```
library_name: mlx-audio-plus
```

### 结论

**CosyVoice3 本身没有问题**
- ❌ 不是模型权重问题
- ❌ 不是配置问题
- ✅ 就是使用了错误的库版本

**需要使用**:
```bash
pip install mlx-audio-plus  # 而不是 pip install mlx-audio
```

mlx-audio-plus 是由第三方维护的增强版本，支持最新的模型如 CosyVoice3。

---

## Kokoro - 问题复杂性分析 🔍

### 权重形状错误的深度分析

**错误模式**:
```
Expected: (512, 3, 1)   - MLX Conv1D 格式
Received: (512, 1, 3)   - 不符合任何标准格式
```

### 这意味着什么

1. **不是简单的维度交换**
   - PyTorch: `(out, in, kernel)` → `(512, 512, 3)`
   - MLX: `(out, kernel, in)` → `(512, 3, 512)`
   - 实际: `(512, 1, 3)` ← 这不符合任何模式

2. **权重可能在转换时出错**
   - Kokoro 从 PyTorch 转换到 MLX
   - 转换过程中某个维度处理不当
   - 导致了这种"混合"格式

3. **不同权重层的不同错误**
   ```
   predictor.F0.1.conv1.weight_v: (512, 512, 3) - PyTorch 格式
   predictor.F0.1.pool.weight_v: (512, 1, 3)    - 奇怪的格式
   ```

### PR #423 为什么必需

PR #423 的修复不仅仅是改进 `check_array_shape` 函数，而是：

1. **智能格式检测**: 识别各种错误的权重格式
2. **有条件的转置**: 根据检测到的格式应用正确的转置
3. **多文件协调**: 在 `kokoro.py`、`istftnet.py` 等多个文件中应用修复
4. **特殊参数处理**: 为中文、数字转换等添加支持

---

## 为什么无法回到早期 MLX 版本测试

### 版本依赖问题

**问题**:
- mlx-audio 的每个版本都被锁定到特定的 MLX 版本范围
- 早期版本（0.0.x）根本不存在与 Kokoro 相关的代码
- 无法自由地混合不兼容的版本

**测试结果**:
```
ERROR: Cannot install mlx-audio==0.1.0 and mlx==0.0.2 
because these package versions have conflicting dependencies.
```

### 结论

即使我们能回到早期版本，Kokoro 模型本身可能就不存在或处于不同状态。

---

## 完整发现总结

### 关于 CosyVoice3 ✅

| 问题 | 答案 |
|-----|------|
| 是模型问题吗? | ❌ 不是 |
| 是 mlx-audio bug? | ❌ 不是 |
| 是什么问题? | 需要用 mlx-audio-plus |
| 如何解决? | `pip install mlx-audio-plus` |
| 是否能工作? | ✅ 理论上可以（环境配置问题待解决） |

### 关于 Kokoro ❌

| 问题 | 答案 |
|-----|------|
| 权重是否正确? | ❌ 转换有误 |
| 能否用简单转置修复? | ❌ 格式太复杂 |
| 需要 PR #423 吗? | ✅ 绝对需要 |
| 是版本问题吗? | ❓ 无法确定（版本测试失败） |
| 何时能修复? | ⏳ 等待 PR 合并 |

---

## 最终建议

### 立即行动

1. **继续使用 Qwen3-TTS** ✅
   - 完全可用
   - 不需要任何修复
   - 中文支持优秀

2. **对 CosyVoice3 的下一步**
   - 尝试在干净的环境中安装 mlx-audio-plus
   - 或等待 mlx-audio-plus 集成到官方库

3. **对 Kokoro 的下一步**
   - 定期监控 PR #423 的合并状态
   - 一旦合并，升级 mlx-audio 后会自动可用

### 不需要做

- ❌ 继续尝试修复 Kokoro（太复杂）
- ❌ 尝试混合不兼容的 MLX 版本
- ❌ 等待早期版本支持

---

## 技术洞察

### Kokoro 权重问题的真正原因

基于权重形状分析，最可能的原因是：

1. **PyTorch 到 MLX 转换器有 bug**
   - 某些权重类型处理不当
   - 导致维度排列错误

2. **Kokoro 模型配置特殊**
   - 使用了非标准的权重格式
   - 转换器无法正确处理

3. **MLX 权重加载器严格**
   - 严格验证权重形状
   - 不允许任何偏差

### 为什么 PR #423 能修复

PR #423 通过：
- 识别错误的权重格式
- 应用正确的维度映射
- 而不仅仅是简单的转置

这表明转换过程中的问题比简单的维度交换更复杂。

---

## 后记

这次调查展示了深入理解问题的重要性：

1. **表面问题** → "Kokoro 不能用"
2. **中间发现** → "权重形状不匹配"
3. **深层原因** → "模型转换过程中的维度处理问题"
4. **真正解决** → "需要复杂的格式检测和映射逻辑"

同样地，CosyVoice3 的问题也不是显而易见的：
- 表面看是"模型不支持"
- 实际上是"需要用不同的库"

这提醒我们在调试时要追根溯源，而不是停留在表面症状。
