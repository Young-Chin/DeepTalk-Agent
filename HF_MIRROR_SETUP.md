# 模型下载加速指南

## 问题背景

MLX Audio 默认从 HuggingFace 下载模型，国内用户可能会遇到：
- 下载速度极慢（<10KB/s）
- 连接超时
- 认证失败

## 解决方案：使用 HF-Mirror

HF-Mirror（https://hf-mirror.com）是 HuggingFace 的国内镜像站，可以显著加速模型下载。

### 方法 1: 环境变量（推荐）

在 `.env` 文件中添加：

```bash
HF_ENDPOINT=https://hf-mirror.com
```

或者在运行时设置：

```bash
export HF_ENDPOINT=https://hf-mirror.com
python3 -m app.main
```

### 方法 2: 永久配置

添加到 `~/.bashrc` 或 `~/.zshrc`：

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

然后执行：
```bash
source ~/.bashrc  # 或 source ~/.zshrc
```

## 验证配置

检查环境变量是否生效：

```bash
echo $HF_ENDPOINT
# 应该输出：https://hf-mirror.com
```

## 模型存储位置

下载的模型会缓存在：

- macOS/Linux: `~/.cache/huggingface/hub/`
- Windows: `C:\Users\<用户名>\.cache\huggingface\hub\`

### 清除缓存重新下载

如果模型损坏或需要重新下载：

```bash
# 清除特定模型
rm -rf ~/.cache/huggingface/hub/models--mlx-community--VibeVoice*

# 清除所有 MLX 模型
rm -rf ~/.cache/huggingface/hub/models--mlx-community--*

# 然后重新运行程序
python3 -m app.main
```

## 常用模型路径

使用 HF-Mirror 后，模型路径保持不变：

```bash
# VibeVoice (推荐，低延迟流式)
mlx-community/VibeVoice-Realtime-0.5B-4bit

# Kokoro (极速)
mlx-community/Kokoro-82M-4bit

# Qwen3-TTS (高质量)
mlx-community/Qwen3-TTS-12Hz-0.6B-Base-4bit

# Qwen3-ASR
mlx-community/Qwen3-ASR-0.6B-4bit
```

## 切换 TTS 模型

在 `.env` 中设置：

```bash
# 使用 VibeVoice（默认推荐）
MLX_TTS_MODEL_TYPE=vibevoice

# 使用 Kokoro（最快）
MLX_TTS_MODEL_TYPE=kokoro

# 使用 Qwen3-TTS（最佳音质）
MLX_TTS_MODEL_TYPE=qwen3
```

## 故障排查

### 问题 1: 设置了 HF_ENDPOINT 但仍然很慢

**解决**：
1. 确认环境变量已生效：`echo $HF_ENDPOINT`
2. 清除 DNS 缓存：`sudo dscacheutil -flushcache` (macOS)
3. 尝试重启终端或 IDE

### 问题 2: 认证错误

**错误**: `Invalid username or password`

**原因**: HF-Mirror 不需要认证，但某些工具可能仍尝试访问 HuggingFace

**解决**:
```bash
# 确保只使用 HF_ENDPOINT，不要设置 HF_TOKEN
unset HF_TOKEN
export HF_ENDPOINT=https://hf-mirror.com
```

### 问题 3: 模型加载失败

**错误**: `Repository Not Found`

**解决**:
1. 检查模型名称是否正确（应该是 `mlx-community/xxx` 而不是 `modelscope/xxx`）
2. 清除缓存重新下载
3. 确认 HF_ENDPOINT 设置正确

## 其他镜像源

如果 HF-Mirror 不可用，还可以尝试：

- **Gitee AI**: https://ai.gitee.com
- **ModelScope**: https://modelscope.cn（需要单独配置）

## 性能对比

| 下载源 | 速度（北京） | 稳定性 |
|--------|-------------|--------|
| HuggingFace 官方 | <10KB/s | 差 |
| HF-Mirror | 1-5MB/s | 好 |
| 本地缓存 | instant | 最佳 |

## 相关资源

- HF-Mirror 官网：https://hf-mirror.com
- HuggingFace 中国社区：https://huggingface.co/zh
- MLX Audio 文档：https://github.com/Blaizzy/mlx-audio
