# DeepTalk Agent CLI

本项目是一个本地 CLI Demo，用来验证中文访谈播客的人机闭环：

麦克风输入 -> ASR -> 主持人式 LLM 回复 -> TTS 播放（支持半双工打断）

---

## 快速开始（推荐）

目标：只改最少参数就能跑通完整链路。

### 1) 安装依赖

```bash
python3 -m pip install -r requirements.txt
python3 -m pip install -U mlx-audio
```

### 2) 准备配置

```bash
cp .env.example .env
```

默认已经启用本地 ASR + 本地 TTS（MLX）。  
你只需要至少填好这 3 个参数：

```bash
GEMINI_API_KEY=你的可用 token
LLM_BASE_URL=https://model-api.skyengine.com.cn/v1/chat/completions
LLM_MODEL=qwen3.5-flash
```

**国内用户加速**：如果下载模型速度慢，在 `.env` 中添加：
```bash
HF_ENDPOINT=https://hf-mirror.com
```

或者运行时设置环境变量：
```bash
export HF_ENDPOINT=https://hf-mirror.com
python3 -m app.main
```

### 3) 先跑自检

```bash
PODCAST_SELF_TEST=1 python3 -m app.main
```

### 4) 跑完整语音模式

```bash
python3 -m app.main
```

---

## 默认配置说明（开箱即用）

`.env.example` 默认是：

- `ASR_BACKEND=mlx`
- `TTS_BACKEND=mlx_qwen3`
- `MLX_TTS_MODEL_TYPE=qwen3`

即默认优先走本地模型链路，不依赖远端 ASR/TTS 服务。

---

## 可选 TTS 模型（本地）

当前 `TTS_BACKEND=mlx_qwen3` 下，可通过 `MLX_TTS_MODEL_TYPE` 选择模型：

- `qwen3`（默认）
- `vibevoice`
- `kokoro`

示例：

```bash
MLX_TTS_MODEL_TYPE=qwen3
# 或 vibevoice / kokoro
```

对应模型路径变量：

- `MLX_TTS_QWEN3_MODEL`
- `MLX_TTS_VIBEVOICE_MODEL`
- `MLX_TTS_KOKORO_MODEL`

其他常用参数：

- `MLX_TTS_LANGUAGE=zh`
- `MLX_TTS_VOICE=`（可留空）
- `MLX_TTS_SPEED=1.0`

---

## 模型下载（首次运行必读）

程序会在首次运行时自动下载所需模型。

**国内用户加速**：强烈建议配置 HF-Mirror，详见 [HF_MIRROR_SETUP.md](HF_MIRROR_SETUP.md)

```bash
# 方法 1: 在 .env 中设置
echo "HF_ENDPOINT=https://hf-mirror.com" >> .env

# 方法 2: 运行时设置
export HF_ENDPOINT=https://hf-mirror.com
python3 -m app.main
```

**模型缓存位置**: `~/.cache/huggingface/hub/`  
**清除缓存**: `rm -rf ~/.cache/huggingface/hub/models--mlx-community--*`

### 模型大小参考

- Qwen3-ASR: ~500MB
- VibeVoice-Realtime: ~700MB
- Kokoro-82M: ~200MB
- Qwen3-TTS: ~800MB

首次启动会较慢（取决于网络），请耐心等待下载完成。

---

## 可选：切换远端后端

### 远端 ASR（Qwen）

```bash
ASR_BACKEND=qwen
QWEN_ASR_BASE_URL=http://localhost:8001
```

### 远端 TTS（Fish）

```bash
TTS_BACKEND=fish
FISH_TTS_BASE_URL=http://localhost:8002
```

---

## 运行模式

### 1) 文字链路验证（不打开麦克风）

```bash
PODCAST_TEXT_DEMO="请先做一个简短的自我介绍" python3 -m app.main
```

用于快速检查 `LLM + TTS + 播放`。

### 2) 音频文件链路验证（不真人口播）

```bash
PODCAST_DEMO_AUDIO=tmp/demo/input.wav python3 -m app.main
```

建议 16kHz 单声道 wav。

### 3) 按键录入模式（Push-to-talk）

```bash
PODCAST_PTT=1 python3 -m app.main
```

操作方式：

- 按任意键开始录音
- 再按任意键停止录音并触发转写

---

## Mock 模式

如果你暂时不想依赖真实模型服务：

```bash
PODCAST_BACKEND=mock python3 -m app.main
```

---

## 常见问题

- `mlx-audio is required ...`  
  先执行：`python3 -m pip install -U mlx-audio`

- 启动后听不到声音  
  先跑 `PODCAST_SELF_TEST=1 python3 -m app.main`，检查输出设备和 Playback 状态。

