# Kokoro PR #423 修复尝试结果

## 测试结果

### ❌ 第一次尝试：仅修复 `check_array_shape`

**修改内容**：改进了 `check_array_shape` 函数的检测逻辑

**错误**：
```
ValueError: Expected shape (512, 3, 512) but received shape (512, 512, 3) 
for parameter predictor.F0.1.conv1.weight_v
```

**原因**：只修复了检测逻辑还不够

---

### ⚠️ 第二次尝试：更精确的启发式规则

**修改内容**：使用"kernel_size 总是很小"的规则

```python
# 新规则：如果中间维度很小且小于最后维度，就是 MLX 格式
if middle < 20 and middle < last:
    return True  # MLX format
```

**新错误**：
```
ValueError: Expected shape (512, 3, 1) but received shape (512, 1, 3)
for parameter predictor.F0.1.pool.weight_v
```

**现象**：进步了，但仍然需要不同的转置方式

---

## 根本问题分析

PR #423 的修复不仅仅是改进 `check_array_shape`。根据 PR 描述，它还包括：

1. ✅ **修复权重检测逻辑** - 已尝试
2. ❌ **在多个文件中应用条件转置** - 未完成
3. ❌ **添加中文/Bopomofo 支持** - 未进行
4. ❌ **添加数字转换** - 未进行

### 需要修改的文件

- `base.py` - `check_array_shape` 函数 ✅ 已修复
- `kokoro.py` - `sanitize` 方法中的权重处理 ⚠️ 部分修复
- `istftnet.py` - 解码器中的权重处理 ❌ 未修改
- `modules.py` - 其他权重处理 ❌ 未修改

---

## 为什么完整修复很困难

### 问题 1：多层级的权重处理

错误来自多个不同的层：
- `predictor.F0.1.conv1.weight_v` - 卷积权重
- `predictor.F0.1.pool.weight_v` - 池化权重
- 其他未知位置的权重

每个层可能需要不同的处理逻辑。

### 问题 2：转置维度不确定

仅有的 `.transpose(0, 2, 1)` 不适用于所有情况：
- `(512, 512, 3)` → `(512, 3, 512)` ✓ 可以用 `(0, 2, 1)`
- `(512, 1, 3)` → `(512, 3, 1)` ✗ 无法用 `(0, 2, 1)`

需要更复杂的转置逻辑或特殊处理。

---

## 结论

### 手动修复不可行

PR #423 的完整修复非常复杂，不能通过简单修改 `check_array_shape` 完成。原因：

1. **涉及多个文件的修改**
2. **权重处理逻辑变化多端**
3. **不同层需要不同的转置方式**
4. **可能需要架构级的更改**

### 推荐方案

**放弃手动修复，等待官方合并**

| 方案 | 优点 | 缺点 | 优先级 |
|-----|-----|-----|--------|
| 等待 PR 合并 | 完全解决，官方支持 | 不知道何时合并 | ⭐⭐⭐⭐⭐ |
| 继续用 Qwen3 | 稳定，现在就能用 | 无法用 Kokoro | ⭐⭐⭐⭐⭐ |
| 手动 monkey-patch | 可能有效 | 复杂，容易出错 | ⭐⭐ |
| 升级 MLX 版本 | 可能新版本支持 | 风险未知 | ⭐⭐⭐ |

---

## 后续行动

### 立即（今天）

继续使用 **Qwen3-TTS**（稳定、可用、性能良好）

```bash
# 确认配置
grep MLX_TTS_MODEL_TYPE .env
# 应该输出: MLX_TTS_MODEL_TYPE=qwen3
```

### 长期（定期）

1. **监控 PR #423 进度**
   - GitHub: https://github.com/Blaizzy/mlx-audio/pull/423
   - 关键词：Kokoro, shape mismatch, ZH model

2. **监控官方 mlx-audio 发布**
   - PyPI: https://pypi.org/project/mlx-audio/
   - 检查 Release Notes 中是否提及 Kokoro 修复

3. **定期测试升级**
   ```bash
   pip install --upgrade mlx-audio
   python3 -m app.tests.test_tts_comprehensive --all
   ```

---

## 备份和恢复

如果需要恢复到未修改状态：

```bash
cp /Library/Frameworks/Python.framework/Versions/3.10/lib/python3.10/site-packages/mlx_audio/tts/models/base.py.backup \
   /Library/Frameworks/Python.framework/Versions/3.10/lib/python3.10/site-packages/mlx_audio/tts/models/base.py
```

验证：

```bash
python3 -c "from mlx_audio.tts.models.base import check_array_shape; print(check_array_shape.__doc__)"
```

---

## 总结

| 项目 | 状态 |
|-----|------|
| Kokoro 可用性 | ❌ 仍需等待 |
| 手动修复可行性 | ❌ 太复杂 |
| Qwen3 替代方案 | ✅ 推荐继续使用 |
| 长期监控 | ✅ 应该进行 |

**建议：保持当前 Qwen3-TTS 配置，定期检查官方更新。**
