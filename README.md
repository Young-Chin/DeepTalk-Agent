# 🎙️ DeepTalk Agent CLI

> 🎧 本地播客访谈 AI 助手 | 麦克风输入 → ASR → LLM → TTS 播放（支持半双工打断）

---

## 🚀 快速开始

### 1️⃣ 安装

```bash
pip install -r requirements.txt
pip install -U mlx-audio
```

### 2️⃣ 配置

```bash
cp .env.example .env
```

填入 **必需的 3 个参数**（ASR 和 TTS 会自动下载）：

```bash
GEMINI_API_KEY=your_api_key
LLM_BASE_URL=https://model-api.skyengine.com.cn/v1/chat/completions
LLM_MODEL=qwen3.5-flash
```

> 💡 **国内用户下载慢？** 在 `.env` 中添加：`HF_ENDPOINT=https://hf-mirror.com`

### 3️⃣ 运行

```bash
# 🩺 自检（验证设备和模型）
PODCAST_SELF_TEST=1 python3 -m app.main

# 🎬 完整模式
python3 -m app.main
```

---

## ⚙️ 配置选项

### 📦 默认配置

- ✅ **ASR**: Qwen3-ASR（本地离线，~500MB）
- ✅ **TTS**: Qwen3-TTS（本地离线，~800MB）
- 🔌 **LLM**: 通过 API

> 🌟 所有模型首次运行时自动下载，之后完全离线。

### 🎵 可选 TTS 模型

| 模型 | 大小 | 特点 | 配置 |
|------|------|------|------|
| 🤖 **Qwen3** | 800MB | 多语言，音质清晰 | `MLX_TTS_MODEL_TYPE=qwen3` |
| ⚡ **VibeVoice** | 700MB | 实时流式，低延迟 | `MLX_TTS_MODEL_TYPE=vibevoice` |
| 🐦 **Kokoro** | 200MB | 轻量级，快速 | `MLX_TTS_MODEL_TYPE=kokoro` |

### 🗣️ Kokoro 人声（仅 Kokoro）

```bash
MLX_TTS_VOICE=af_bella        # 👩 女性高音（默认）
MLX_TTS_VOICE=af_sarah        # 👩 女性自然
MLX_TTS_VOICE=am_adam         # 👨 男性低沉
MLX_TTS_VOICE=am_michael      # 👨 男性标准
MLX_TTS_SPEED=1.0             # 🐌🏃 语速（0.5-2.0）
```

### 🎛️ 通用参数

```bash
MLX_TTS_LANGUAGE=zh           # 🌍 语言
MLX_ASR_LANGUAGE=zh           # 🎤 ASR 语言
AUDIO_SAMPLE_RATE=16000       # 📊 采样率
```

---

## 🎮 运行模式

| 模式 | 命令 | 用途 |
|------|------|------|
| ✍️ 文字测试 | `PODCAST_TEXT_DEMO="..." python3 -m app.main` | 快速验证 LLM+TTS+播放 |
| 🎵 音频文件 | `PODCAST_DEMO_AUDIO=path/to/audio.wav python3 -m app.main` | 不依赖麦克风 |
| 🎹 Push-to-talk | `PODCAST_PTT=1 python3 -m app.main` | 按键录音 |
| 🎭 Mock 模式 | `PODCAST_BACKEND=mock python3 -m app.main` | 离线测试 |

---

## ☁️ 远端后端（可选）

如需使用远端 ASR/TTS 服务：

```bash
# 🌐 远端 ASR（Qwen）
ASR_BACKEND=qwen
QWEN_ASR_BASE_URL=http://localhost:8001

# 🐟 远端 TTS（Fish）
TTS_BACKEND=fish
FISH_TTS_BASE_URL=http://localhost:8002
```

---

## ❓ FAQ

**❓ Q: 启动很慢？**  
💡 A: 首次运行会自动下载模型（取决于网络）。可配置 HF-Mirror 加速。

**❓ Q: 听不到声音？**  
🔊 A: 运行 `PODCAST_SELF_TEST=1 python3 -m app.main` 检查设备。

**❓ Q: `mlx-audio` 报错？**  
📦 A: 执行 `pip install -U mlx-audio`

**❓ Q: 清除模型缓存？**  
🗑️ A: `rm -rf ~/.cache/huggingface/hub/models--mlx-community--*`

---

## 🏗️ 架构

```
🎤 麦克风 → 🔤 ASR（Qwen3） → 🧠 LLM（API） → 🔊 TTS（可选） → 🔈 扬声器
              └─ 📦 本地离线          └─ ⚡ 支持打断
```

---

## 💻 环境要求

- 🐍 Python 3.8+
- 🍎 macOS / 🐧 Linux（需要 sounddevice）
- 🌐 网络连接（仅用于下载模型和 API 调用）

---

> 📚 **更多信息**: 见 `.env.example` 了解所有可配置项。
