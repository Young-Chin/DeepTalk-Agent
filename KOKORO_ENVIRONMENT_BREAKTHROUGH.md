# 🚨 Kokoro 在不同环境中行为不同 - 重大突破

## 现象

### 我的环境 (当前 Python 3.10 全局环境)
```python
from mlx_audio.tts.utils import load_model
model = load_model("mlx-community/Kokoro-82M-bf16")
```

**结果**: ❌ 失败
```
ValueError: Expected shape (512, 3, 1) but received shape (512, 1, 3) 
for parameter predictor.F0.1.pool.weight_v
```

### 你的环境 (uv 虚拟环境 .kokoro)
```bash
mlx_audio.tts.generate --model mlx-community/Kokoro-82M-bf16 \
  --text 'Hello!' --play --lang_code a
```

**结果**: ✅ 成功！能正常生成和播放音频

---

## 这意味着什么

### 不是 Kokoro 模型问题
- ✅ 模型本身没问题
- ✅ 能在某些环境中完美工作
- ✅ 能生成可播放的音频

### 是环境配置问题
- 🔍 Python 版本差异?
- 🔍 MLX 版本差异?
- 🔍 mlx-audio 版本差异?
- 🔍 其他依赖差异?

### 可能的原因列表

1. **MLX 版本差异**
   - 我用: 0.31.1
   - 你可能用: 更早或更新的版本?
   - 会影响卷积权重处理

2. **mlx-audio 版本差异**
   - 我用: 0.4.2
   - 你可能用: 不同的版本?
   - 可能有权重处理的补丁

3. **Python 版本差异**
   - 我用: 3.10
   - 你用: 3.11+ 或 3.9?
   - 影响数组处理

4. **模型缓存**
   - 你的模型可能是预先转换的版本?
   - 不同的 HuggingFace 缓存?

5. **uv 环境的魔法**
   - uv 可能有特殊的处理?
   - 锁定了特定的版本组合?

---

## 诊断步骤

为了找到关键差异，请在你的 `.kokoro` uv 环境中运行：

### 1️⃣ 环境版本信息
```bash
python --version
python -c "import mlx; print(f'MLX: {mlx.__version__}')"
python -c "import mlx_audio; print(f'mlx-audio: {mlx_audio.__version__}')"
```

### 2️⃣ 查看配置文件
```bash
# 如果有 pyproject.toml
cat pyproject.toml | grep -A 20 "dependencies\|tool.uv"

# 如果有 uv.lock
head -50 uv.lock

# 或 requirements.txt
cat requirements.txt | grep -E "mlx|torch"
```

### 3️⃣ 完整的依赖列表
```bash
pip list | grep -E "(mlx|torch|audio|numpy|scipy)"
```

### 4️⃣ Kokoro 权重详细信息
```bash
python << 'EOF'
from mlx_audio.tts.utils import load_model
from huggingface_hub import hf_hub_download
import json

# 下载配置
config_path = hf_hub_download(
    repo_id="mlx-community/Kokoro-82M-bf16",
    filename="config.json",
    repo_type="model"
)

with open(config_path) as f:
    config = json.load(f)
    print(json.dumps(config, indent=2)[:500])

# 尝试加载模型
try:
    model = load_model("mlx-community/Kokoro-82M-bf16")
    print("\n✓ 模型加载成功！")
except Exception as e:
    print(f"\n✗ 模型加载失败: {e}")
EOF
```

---

## 为什么这个发现很重要

### 1. 证明 Kokoro 本身没问题
- PR #423 可能不是必需的
- 或者已经在某个版本中被集成
- 或者某个版本中被偶然修复了

### 2. 指向具体的版本问题
- 不是所有版本都有问题
- 可能是 MLX 0.31.1 特有的问题
- 早期或未来版本可能已修复

### 3. 可能简化我们的方案
- 可能不需要等待 PR #423 合并
- 可能升级或降级版本就能解决
- 可能 uv 有特殊的优化

---

## 下一步

等待你提供以下信息：

```bash
# 直接在你的 .kokoro 环境中运行这些命令并给我结果：

echo "=== Python 版本 ==="
python --version

echo "=== MLX 版本 ==="
python -c "import mlx; print(mlx.__version__)"

echo "=== mlx-audio 版本 ==="
python -c "import mlx_audio; print(mlx_audio.__version__)"

echo "=== MLX Audio 下的 kokoro 模块 ==="
python -c "from mlx_audio.tts.models import kokoro; print('✓ kokoro 模块可用')"

echo "=== 完整的 MLX 相关包 ==="
pip list | grep -i mlx

echo "=== pyproject.toml (如果有) ==="
cat pyproject.toml 2>/dev/null | head -30
```

---

## 我的假设

基于你能成功运行 Kokoro，我的初步假设是：

**最可能**: MLX 版本问题
- 你可能用的 MLX 版本**不是** 0.31.1
- 早期版本（0.25-0.30）可能没有这个问题
- 或者新版本（0.32+）已经修复了

**其次**: uv 环境有特殊配置
- 可能锁定了兼容的版本组合
- 可能有特殊的 build 配置

**再次**: 模型缓存差异
- 你的模型可能是不同的版本
- 或者被正确转换过

---

## 关键发现

这个发现**颠覆了之前的所有假设**：

- ✅ Kokoro 模型本身完全可用
- ✅ 能生成实际的音频
- ✅ 能播放音频
- ❓ 但只在特定环境配置下工作

这意味着**不是 Kokoro 本身的问题，而是环境问题**！

---

请提供你的环境信息，我们一起找出关键差异！
