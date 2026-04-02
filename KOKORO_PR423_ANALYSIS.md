# PR #423 对 Kokoro 问题的解决分析

## PR 概览

**标题**: Fix Kokoro ZH model shape mismatch and add mixed language support

**状态**: Closed (Draft) - 2026-03-16 关闭，但未合并到主分支

**源**: https://github.com/Blaizzy/mlx-audio/pull/423

**关键信息**：
- PR 确实针对我们遇到的 Kokoro 形状不匹配问题
- 但目前 **未被合并到官方 mlx-audio**
- 代码存在于 FluidInference 分支

---

## 问题解决方案详解

### 核心修复

根据 PR 描述，以下是对 Kokoro 问题的解决方案：

#### 1. **修复 `check_array_shape` 函数**
```
问题: 无法正确检测 MLX vs PyTorch 的卷积权重格式差异
解决: 改进形状检测逻辑，区分 1D 卷积的不同维度排列
```

这正是我们遇到的问题根源！

#### 2. **权重处理改进**
```python
# 之前（无条件转置）
weights = weights.transpose(...)

# 之后（格式检测后有条件转置）
if is_pytorch_format:
    weights = weights.transpose(...)
else:
    # MLX 格式，保持不变
    pass
```

在 `kokoro.py` 和 `istftnet.py` 中应用

#### 3. **中文特定优化**
- **Bopomofo 转换**：Kokoro ZH 模型使用注音符号（Bopomofo），不是 IPA
  - 新增依赖：`pypinyin`
  - 功能：中文 → 注音符号转换
  
- **数字处理**：支持数字转中文
  - 例：`"23"` → `"二十三"`
  
- **混合语言处理**：中英文混合文本支持
  - 例：`"今天天气很好。Hello, how are you?"`

---

## 完整测试验证

PR 包含的测试覆盖（已验证）：

- ✅ Kokoro-82M-v1.1-zh 模型加载无形状错误
- ✅ 中文 TTS 输出正确（`lang_code="z"`）
- ✅ 混合中英文文本处理
- ✅ 数字在中文文本中的处理
- ✅ 生成音频转录与输入文本一致

---

## 目前的状况

### ❌ 为什么 PR 未合并？

1. **Draft 状态**：PR 仍为草稿（Draft）
2. **可能原因**：
   - 等待 API 稳定
   - 依赖冲突（需要 `pypinyin`）
   - 官方不确定是否接受

### 📦 代码位置

- **分支**：`FluidInference/mlx-audio:fix/kokoro-zh-shape-mismatch`
- **提交**：`0fdfd0d908c4c74dfb1a3e1b05c4ab60ece27a03`
- **仓库**：https://github.com/FluidInference/mlx-audio

---

## 使用这个修复的两种方式

### 方案 A：从 FluidInference 分支安装（推荐先尝试）

```bash
# 1. 备份当前环境
pip freeze > requirements_backup.txt

# 2. 从修复分支安装 mlx-audio
pip install git+https://github.com/FluidInference/mlx-audio.git@fix/kokoro-zh-shape-mismatch

# 3. 测试 Kokoro
python3 -m app.tests.test_tts_comprehensive --model kokoro --diagnose

# 4. 如果失败，恢复
pip install -r requirements_backup.txt
pip install mlx-audio==0.4.2
```

### 方案 B：手动应用修复（不依赖 PR）

如果方案 A 失败，可以手动应用修复：

```bash
# 1. 定位 mlx-audio 安装位置
python3 -c "import mlx_audio; print(mlx_audio.__file__)"

# 2. 应用修复（需要理解代码）
# - 修改 check_array_shape 函数
# - 修改 kokoro.py 中的权重处理
# - 添加 Bopomofo 转换支持
```

---

## 影响分析

### ✅ 优点

1. **直接解决 Kokoro 形状问题**
2. **添加完整的中文支持**
3. **混合语言能力**
4. **经过测试验证**

### ⚠️ 风险

1. **新依赖**：需要 `pypinyin`
   ```bash
   pip install pypinyin
   ```

2. **未在官方版本中**：不是正式发布
   - 后续维护不确定
   - 可能与新版 MLX 冲突

3. **Draft 状态**：可能有未知问题
   - PR 作者可能停止维护
   - 代码可能未完全测试

---

## 推荐的升级路径

### 短期方案（本周）

```
1. 保持当前 Qwen3-TTS（稳定）
2. 尝试从 FluidInference 分支安装修复
3. 运行完整测试验证是否可用
```

### 中期方案（下周）

```
如果 FluidInference 分支有效：
- 继续使用它
- 监控官方 mlx-audio 是否合并相似修复
- 记录兼容性问题

如果 FluidInference 分支无效：
- 继续使用 Qwen3-TTS
- 等待官方修复或新版本
```

### 长期方案（本月）

```
关注官方 mlx-audio 进展：
- Issue 跟踪：Kokoro shape mismatch
- 新版本发布：可能包含官方修复
- 定期检查最新版本是否支持
```

---

## 测试建议

如果要尝试这个修复，建议按此顺序：

```bash
# 步骤 1: 备份当前环境
pip freeze > requirements_backup_kokoro.txt

# 步骤 2: 安装修复版本
pip install git+https://github.com/FluidInference/mlx-audio.git@fix/kokoro-zh-shape-mismatch

# 步骤 3: 安装额外依赖（如果需要）
pip install pypinyin

# 步骤 4: 运行诊断
python3 -m app.tests.diagnose_vibevoice_language  # 测试基础功能
python3 -m app.tests.test_tts_comprehensive --model kokoro --diagnose

# 步骤 5: 手动测试
python3 -c "
import asyncio
from app.tts.qwen_adapter import MLXQwenTTSAdapter

async def test():
    adapter = MLXQwenTTSAdapter(
        model='mlx-community/Kokoro-82M-4bit',
        lang_code='z',  # 中文
        speed=1.0,
    )
    audio = await adapter.synthesize('你好，世界')
    print(f'成功！音频大小: {len(audio)} bytes')

asyncio.run(test())
"

# 步骤 6: 如果成功，更新 .env
# MLX_TTS_MODEL_TYPE=kokoro

# 步骤 7: 如果失败，恢复
pip install -r requirements_backup_kokoro.txt
```

---

## 相关资源

| 资源 | 链接 |
|-----|------|
| PR 讨论 | https://github.com/Blaizzy/mlx-audio/pull/423 |
| 修复分支 | https://github.com/FluidInference/mlx-audio/tree/fix/kokoro-zh-shape-mismatch |
| 提交 | 0fdfd0d908c4c74dfb1a3e1b05c4ab60ece27a03 |
| 官方 mlx-audio | https://github.com/Blaizzy/mlx-audio |

---

## 总结

这个 PR **正是解决我们问题的方案**，但有以下限制：

| 方面 | 状态 |
|-----|------|
| 解决形状问题 | ✅ 是 |
| 添加中文支持 | ✅ 是 |
| 测试验证 | ✅ 是 |
| 官方发布 | ❌ 否 |
| 风险等级 | ⚠️ 中等 |

**建议**：值得一试，但要做好备份和测试准备。
