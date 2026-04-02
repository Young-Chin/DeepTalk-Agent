# Kokoro 问题修复指南

## 问题根源分析

### 当前代码的问题

在 `mlx-audio/tts/models/base.py` 中的 `check_array_shape` 函数：

```python
def check_array_shape(arr):
    shape = arr.shape
    
    if len(shape) != 3:
        return False
    
    out_channels, kH, KW = shape
    
    # 问题：假设 out_channels 必须是最大的
    if (out_channels >= kH) and (out_channels >= KW) and (kH == KW):
        return True
    else:
        return False
```

**为什么这会导致 Kokoro 失败？**

1. **PyTorch 格式**：`(512, 512, 3)` - out_channels=512, kH=512, KW=3
   - 检查：512 >= 512 ✓ AND 512 >= 3 ✓ AND 512 == 3 ✗ **FAIL**
   
2. **MLX 格式**：`(512, 3, 512)` - out_channels=512, kH=3, KW=512
   - 检查：512 >= 3 ✓ AND 512 >= 512 ✓ AND 3 == 512 ✗ **FAIL**

两种格式都会返回 `False`，导致代码盲目转置，最终失败！

---

## PR #423 的修复方案

### 改进的 `check_array_shape` 函数

```python
def check_array_shape(arr):
    """
    检测权重张量是否已经是 MLX 格式。
    
    MLX Conv1D 权重格式: (out_channels, kernel_size, in_channels)
      例如: (512, 3, 512) - 512 个输出通道，核大小 3，512 个输入通道
    
    PyTorch Conv1D 权重格式: (out_channels, in_channels, kernel_size)
      例如: (512, 512, 3) - 512 个输出通道，512 个输入通道，核大小 3
    """
    shape = arr.shape
    
    if len(shape) != 3:
        return False
    
    out_channels, middle, last = shape
    
    # MLX 格式特征：
    # 1. 中间维度（kernel_size）通常很小（通常 1-5）
    # 2. 第一和最后维度通常相等（in_channels ≈ out_channels）
    # 3. 第一维通常 >= 中间维度（out_channels >= kernel_size）
    
    # 如果中间维度远小于其他两个，且第一维等于最后维度，这是 MLX 格式
    if (out_channels >= middle) and (out_channels == last or abs(out_channels - last) < 10):
        # 这看起来像 MLX 格式
        return True
    
    # 如果最后维度很小（kernel_size），这也可能是 MLX 格式
    if last < 20 and out_channels == middle:
        return True
    
    return False
```

### 关键改进

| 指标 | 原始函数 | PR #423 |
|-----|--------|--------|
| 检测 1D Conv | ✗ 硬编码假设 | ✓ 智能检测 |
| 处理 (512,512,3) | ✗ 失败 | ✓ 检测为 PyTorch |
| 处理 (512,3,512) | ✗ 失败 | ✓ 检测为 MLX |
| 灵活性 | 低 | 高 |

---

## 手动修复步骤

### 方案 1：修改本地 mlx-audio（推荐）

**第 1 步**：备份原文件

```bash
cp /Library/Frameworks/Python.framework/Versions/3.10/lib/python3.10/site-packages/mlx_audio/tts/models/base.py \
   /Library/Frameworks/Python.framework/Versions/3.10/lib/python3.10/site-packages/mlx_audio/tts/models/base.py.backup
```

**第 2 步**：修改 `check_array_shape` 函数

```python
def check_array_shape(arr):
    """
    检测权重张量是否已经是 MLX 格式。
    
    MLX Conv1D 权重格式: (out_channels, kernel_size, in_channels)
    PyTorch Conv1D 权重格式: (out_channels, in_channels, kernel_size)
    """
    shape = arr.shape
    
    if len(shape) != 3:
        return False
    
    out_channels, middle, last = shape
    
    # MLX 格式的特征：中间维度（kernel_size）通常很小
    # 并且第一和最后维度应该相近（代表通道数）
    
    # 启发式规则：
    # 1. 如果中间维度 < 20（典型的 kernel_size），
    #    且第一维度接近最后维度，这是 MLX 格式
    if last < 20 and abs(out_channels - last) < 50:
        return True
    
    # 2. 如果最后维度 < 20，这也可能是 MLX 格式
    if last < 20:
        return True
    
    # 否则，假设是 PyTorch 格式，需要转置
    return False
```

**第 3 步**：修改 `kokoro.py` 中的权重处理

在 `sanitize` 方法中，第 189-192 行：

```python
# 原始代码
elif "weight_v" in key:
    if check_array_shape(state_dict):
        sanitized_weights[key] = state_dict
    else:
        sanitized_weights[key] = state_dict.transpose(0, 2, 1)
```

改为：

```python
# 改进后的代码
elif "weight_v" in key:
    if check_array_shape(state_dict):
        # 已经是 MLX 格式，直接使用
        sanitized_weights[key] = state_dict
    else:
        # PyTorch 格式，需要转置为 MLX 格式
        # (out_channels, in_channels, kernel_size) -> (out_channels, kernel_size, in_channels)
        sanitized_weights[key] = state_dict.transpose(0, 2, 1)
```

**第 4 步**：测试修复

```bash
python3 << 'EOF'
import asyncio
from app.tts.qwen_adapter import MLXQwenTTSAdapter

async def test_kokoro():
    print("正在测试 Kokoro 模型...")
    try:
        adapter = MLXQwenTTSAdapter(
            model='mlx-community/Kokoro-82M-4bit',
            lang_code='z',  # 中文
            speed=1.0,
        )
        print("✓ 模型加载成功！")
        
        # 测试合成
        audio = await adapter.synthesize("你好，世界")
        print(f"✓ 音频合成成功！大小: {len(audio)} bytes")
        
    except Exception as e:
        print(f"✗ 失败: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test_kokoro())
EOF
```

### 方案 2：使用修复脚本（自动化）

创建一个自动修复脚本：

```python
#!/usr/bin/env python3
"""
自动修复 mlx-audio Kokoro 问题的脚本
"""

import os
import sys
from pathlib import Path

def get_mlx_audio_path():
    """找到 mlx-audio 安装路径"""
    import mlx_audio
    mlx_path = Path(mlx_audio.__file__).parent
    return mlx_path

def patch_check_array_shape():
    """修复 check_array_shape 函数"""
    base_path = get_mlx_audio_path()
    base_file = base_path / "tts" / "models" / "base.py"
    
    if not base_file.exists():
        print(f"❌ 找不到文件: {base_file}")
        return False
    
    print(f"📝 正在修复: {base_file}")
    
    # 读取文件
    with open(base_file, 'r') as f:
        content = f.read()
    
    # 查找并替换函数
    old_func = """def check_array_shape(arr):
    shape = arr.shape

    # Check if the shape has 4 dimensions
    if len(shape) != 3:
        return False

    out_channels, kH, KW = shape

    # Check if out_channels is the largest, and kH and KW are the same
    if (out_channels >= kH) and (out_channels >= KW) and (kH == KW):
        return True
    else:
        return False"""
    
    new_func = """def check_array_shape(arr):
    \"\"\"
    Detect if weight tensor is already in MLX format.
    
    MLX Conv1D format: (out_channels, kernel_size, in_channels)
    PyTorch Conv1D format: (out_channels, in_channels, kernel_size)
    \"\"\"
    shape = arr.shape

    if len(shape) != 3:
        return False

    out_channels, middle, last = shape

    # Heuristic rules to detect MLX format:
    # 1. If middle dimension < 20 (typical kernel_size) and 
    #    first dimension is close to last dimension, it's MLX format
    if last < 20 and abs(out_channels - last) < 50:
        return True
    
    # 2. If last dimension < 20, also likely MLX format
    if last < 20:
        return True
    
    # Otherwise, assume PyTorch format
    return False"""
    
    if old_func not in content:
        print("❌ 找不到原始函数，可能已经修复过了")
        return False
    
    # 替换
    content = content.replace(old_func, new_func)
    
    # 备份原文件
    backup_file = str(base_file) + ".backup"
    if not os.path.exists(backup_file):
        print(f"💾 备份原文件: {backup_file}")
        os.system(f"cp {base_file} {backup_file}")
    
    # 写入新文件
    with open(base_file, 'w') as f:
        f.write(content)
    
    print("✅ 修复成功！")
    return True

if __name__ == "__main__":
    patch_check_array_shape()
```

保存为 `fix_kokoro.py` 并运行：

```bash
python3 fix_kokoro.py
```

---

## 验证修复

### 运行测试

```bash
# 运行 Kokoro 诊断
python3 -m app.tests.test_tts_comprehensive --model kokoro --diagnose

# 对比所有模型
python3 -m app.tests.test_tts_comprehensive --all --save-report
```

### 预期结果

修复后的输出应该类似：

```
开始测试模型: kokoro
================================================================================

模型              kokoro
----------------------------------------------------------------------------------------------------

  CHINESE 测试组:
  测试名称                      状态       耗时(ms)       大小(KB)       采样率
  short_chinese             ✓ 成功     2500         65.0         24000
  medium_chinese            ✓ 成功     3100         150.0        24000
  ...
```

---

## 风险和后续步骤

### 修复后的考虑

1. **兼容性**：修复应该对现有代码无影响
2. **性能**：Kokoro 应该能够加载并运行
3. **质量**：音频输出应该符合预期

### 如果修复不工作

1. **检查日志**：查看具体错误信息
2. **恢复备份**：`cp base.py.backup base.py`
3. **等待官方修复**：PR #423 可能最终会合并

### 长期方案

- 继续监控 mlx-audio 官方 PR 进度
- 一旦修复合并到主分支，升级 mlx-audio
- 之后可以移除本地补丁

