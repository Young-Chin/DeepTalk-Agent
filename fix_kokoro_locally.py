#!/usr/bin/env python3
"""
自动修复 mlx-audio Kokoro 权重形状问题的脚本

用法:
    python3 fix_kokoro_locally.py
"""

import os
import sys
from pathlib import Path

def get_mlx_audio_path():
    """找到 mlx-audio 安装路径"""
    try:
        import mlx_audio
        mlx_path = Path(mlx_audio.__file__).parent
        return mlx_path
    except ImportError:
        print("❌ 找不到 mlx-audio，请先安装: pip install mlx-audio")
        return None

def patch_check_array_shape():
    """修复 base.py 中的 check_array_shape 函数"""
    mlx_path = get_mlx_audio_path()
    if not mlx_path:
        return False
    
    base_file = mlx_path / "tts" / "models" / "base.py"
    
    if not base_file.exists():
        print(f"❌ 找不到文件: {base_file}")
        return False
    
    print(f"📝 正在修复: {base_file}")
    
    # 读取文件
    with open(base_file, 'r') as f:
        content = f.read()
    
    # 检查是否已经修复过
    if "Detect if weight tensor is already in MLX format" in content:
        print("✅ 已经修复过了，跳过")
        return True
    
    # 查找原始函数
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
    
    Key insight:
    - kernel_size is always small (typically 1-5)
    - In MLX format, kernel_size is at position [1] (middle)
    - In PyTorch format, kernel_size is at position [2] (last)
    
    For example:
    - MLX: (512, 3, 512) - 512 out, 3 kernel, 512 in
    - PyTorch: (512, 512, 3) - 512 out, 512 in, 3 kernel
    \"\"\"
    shape = arr.shape

    if len(shape) != 3:
        return False

    out_channels, middle, last = shape

    # The key heuristic: kernel_size is always small
    # If middle < last and middle < 20, then middle is likely kernel_size (MLX format)
    # If last < 20, then last is likely kernel_size (PyTorch format, needs transpose)
    
    if middle < 20 and middle < last:
        # Middle dimension is small and smaller than last dimension
        # This is MLX format: (out, kernel, in)
        return True
    
    # Otherwise, it's PyTorch format (out, in, kernel) and needs transpose
    return False"""
    
    if old_func not in content:
        print("❌ 找不到原始函数")
        print("可能已经修复过了或代码结构不同")
        return False
    
    # 替换
    content = content.replace(old_func, new_func)
    
    # 备份原文件
    backup_file = str(base_file) + ".backup"
    if not os.path.exists(backup_file):
        print(f"💾 创建备份: {backup_file}")
        os.system(f"cp {base_file} {backup_file}")
    
    # 写入新文件
    with open(base_file, 'w') as f:
        f.write(content)
    
    print("✅ base.py 修复成功！")
    return True

def main():
    print("="*70)
    print("Kokoro 权重形状问题修复工具")
    print("="*70)
    print()
    
    mlx_path = get_mlx_audio_path()
    if not mlx_path:
        return False
    
    print(f"📦 找到 mlx-audio: {mlx_path}")
    print()
    
    # 执行修复
    if patch_check_array_shape():
        print()
        print("="*70)
        print("✅ 修复完成！")
        print("="*70)
        print()
        print("下一步：测试 Kokoro 模型")
        print()
        print("  python3 -m app.tests.test_tts_comprehensive --model kokoro --diagnose")
        print()
        return True
    else:
        print()
        print("="*70)
        print("❌ 修复失败")
        print("="*70)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
