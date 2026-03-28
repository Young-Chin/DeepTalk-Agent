# DeepTalk Agent CLI MVP

本项目是一个本地 CLI Demo，用来验证中文访谈播客的人机闭环：
麦克风输入 -> ASR -> 主持人式 LLM 回复 -> TTS 播放，并支持半双工打断。

## Quick Start

如果你现在就想在本地试用，建议按这个最短路径来：

1. 安装依赖

```bash
python3 -m pip install -r requirements.txt
python3 -m pip install -U mlx-audio
```

2. 准备环境变量

```bash
cp .env.example .env
```

然后把 `.env` 至少改成这组：

```bash
GEMINI_API_KEY=你的 Bearer token
LLM_BASE_URL=https://model-api.skyengine.com.cn/v1/chat/completions
LLM_MODEL=qwen3.5-flash

ASR_BACKEND=mlx
MLX_ASR_MODEL=mlx-community/Qwen3-ASR-0.6B-4bit
MLX_ASR_LANGUAGE=zh

TTS_BACKEND=mlx_qwen3
MLX_TTS_MODEL=mlx-community/Qwen3-TTS-12Hz-0.6B-Base-4bit
MLX_TTS_LANGUAGE=zh
```

3. 先跑一次自检

```bash
PODCAST_SELF_TEST=1 python3 -m app.main
```

4. 如果你想先不打开麦克风，直接验证 `LLM + TTS + 播放`

```bash
PODCAST_TEXT_DEMO="请先做一个简短的自我介绍" python3 -m app.main
```

5. 如果你想验证 `ASR + LLM + TTS + 播放` 的完整链路，但不想真人口播

先准备一段本地 wav：

```bash
mkdir -p tmp/demo
say -v Tingting -o tmp/demo/input.aiff "你好，请介绍一下你自己。"
afconvert -f WAVE -d LEI16@16000 -c 1 tmp/demo/input.aiff tmp/demo/input.wav
```

然后运行：

```bash
PODCAST_DEMO_AUDIO=tmp/demo/input.wav python3 -m app.main
```

6. 最后再跑真人麦克风模式

```bash
python3 -m app.main
```

## Setup

1. 安装依赖：

```bash
python3 -m pip install -r requirements.txt
```

2. 准备环境变量：

```bash
cp .env.example .env
```

3. 按你的服务地址和密钥填写 `.env`。

如果你要试本地 MLX ASR，还需要额外安装一次可选依赖：

```bash
python3 -m pip install mlx-audio
```

## Run

```bash
python3 -m app.main
```

启动后会进入实时音频循环并持续等待语音输入。

## Text Demo Mode

如果你想在真正打开麦克风前，先确认 `LLM + TTS + 播放` 这半条链路是通的，可以直接跑文本 demo：

```bash
PODCAST_TEXT_DEMO="请先做一个简短的自我介绍" python3 -m app.main
```

text demo 模式会：

- 直接把给定文本当作用户输入
- 调用当前配置的 LLM
- 再调用当前配置的 TTS
- 最后触发本地播放

这条路径很适合在 demo 前快速确认：

- LLM endpoint / token 是否正确
- TTS backend 是否可用
- 扬声器播放是否正常
- 当前本地模型组合是否至少能跑通后半条链路

## Audio Demo Mode

如果你想在不真人口播的前提下，脚本化验证 `ASR -> LLM -> TTS -> 播放` 的完整链路，可以提供一段本地音频：

```bash
PODCAST_DEMO_AUDIO=tmp/demo/input.wav python3 -m app.main
```

说明：

- 支持直接读取 `.wav` 的 PCM 数据。
- 这条路径适合做可重复 demo、回归测试和现场演示前检查。
- 推荐用 16kHz 单声道 wav，这样最接近当前 ASR runtime 的输入形式。

## Local MLX ASR

当前已经支持把 ASR 切到本地 MLX backend。推荐先用下面这组环境变量：

```bash
ASR_BACKEND=mlx
MLX_ASR_MODEL=mlx-community/Qwen3-ASR-0.6B-4bit
MLX_ASR_LANGUAGE=zh
```

然后正常启动：

```bash
python3 -m app.main
```

说明：

- `ASR_BACKEND=qwen` 继续走原来的远端 HTTP ASR。
- `ASR_BACKEND=mlx` 会在本机直接加载 `mlx-community/Qwen3-ASR-0.6B-4bit`。
- 首次启动会下载模型，后续会复用本地缓存。
- 我在这台机器上实测，这个模型对一段约 9 秒中文样本的转写耗时约 `1.95s`，峰值内存约 `1.37 GB`。
- 当前本地 MLX ASR 仍属于 MVP 接入，推理时会把每个语音 chunk 写成临时 WAV 再送进 `mlx-audio`，优先保证能跑通。

## Current Local Model Combo

当前阶段，推荐的本地模型组合是：

- ASR: `mlx-community/Qwen3-ASR-0.6B-4bit`
- TTS: `mlx-community/Qwen3-TTS-12Hz-0.6B-Base-4bit`

选择这组组合的原因很直接：

- 两个模型都已经在这台机器上完成了本地实测。
- ASR 已经接入当前工程，可通过 `ASR_BACKEND=mlx` 启用。
- TTS 已经可以通过 `TTS_BACKEND=mlx_qwen3` 接入当前 runtime。
- 相比之下，`mlx-community/Kokoro-82M-4bit` 当前主要受 `mlx-audio` / `mlx_lm` 版本兼容问题影响，暂不作为默认推进方案。

推荐环境变量：

```bash
ASR_BACKEND=mlx
MLX_ASR_MODEL=mlx-community/Qwen3-ASR-0.6B-4bit
MLX_ASR_LANGUAGE=zh

TTS_BACKEND=mlx_qwen3
MLX_TTS_MODEL=mlx-community/Qwen3-TTS-12Hz-0.6B-Base-4bit
MLX_TTS_LANGUAGE=zh
MLX_TTS_VOICE=
```

说明：

- `TTS_BACKEND=fish` 继续走原来的远端 Fish TTS。
- `TTS_BACKEND=mlx_qwen3` 会在本机直接加载 `mlx-community/Qwen3-TTS-12Hz-0.6B-Base-4bit`。
- 当前 `MLX_TTS_VOICE` 留空即可，先使用模型默认音色；后续可以再补更细的音色选择和 persona 映射。

本地手工验证命令：

```bash
python3 -m mlx_audio.stt.generate \
  --model mlx-community/Qwen3-ASR-0.6B-4bit \
  --audio tmp/asr/sample.wav \
  --output-path tmp/asr/sample.txt \
  --format txt \
  --language zh \
  --verbose
```

```bash
python3 -m mlx_audio.tts.generate \
  --model mlx-community/Qwen3-TTS-12Hz-0.6B-Base-4bit \
  --text "你好，我们现在在测试本地中文语音合成。" \
  --output_path tmp/qwen3_tts \
  --file_prefix qwen3_tts_test \
  --audio_format wav \
  --join_audio \
  --verbose
```

## Mock Mode

在本地 ASR / TTS 服务还没部署完成前，可以先用 mock backend 跑通完整链路：

```bash
PODCAST_BACKEND=mock python3 -m app.main
```

mock 模式下：

- 麦克风和本地播放仍然使用真实音频设备。
- ASR / 主持人回复 / TTS 使用内置 mock backend。
- 不需要配置 `GEMINI_API_KEY`、`QWEN_ASR_BASE_URL`、`FISH_TTS_BASE_URL`。
- 每轮会打印 `User:`、`Host:` 和 `Turn latency:`，更适合拿来做本地联调。

## Self-Test Mode

如果你想先做一次明确的本机诊断，可以直接跑 self-test：

```bash
PODCAST_BACKEND=mock PODCAST_SELF_TEST=1 python3 -m app.main
```

self-test 会打印：

- 当前 ASR backend
- 当前 TTS backend
- 当前 LLM model
- 当前 ASR model
- 当前 TTS model
- 当前输入设备
- 当前输出设备
- 当前播放模式（`real` 或 `memory`）
- 是否检测到 speech frame
- 是否拿到 ASR 文本
- 是否成功生成 TTS 音频
- 是否真正调用了播放

如果当前机器没有安装 `sounddevice` 或 `numpy`，程序会自动退回 `memory` 播放模式，让 mock / dry-run 逻辑继续可用，而不是直接因为本地音频依赖缺失而中断。

## Speaker Check

如果你想先确认本机扬声器链路是否工作，可以优先用 mock 模式：

```bash
PODCAST_BACKEND=mock python3 -m app.main
```

当前 mock TTS 会生成一个很短的本地 WAV 音频片段。实际体验上可以这样测：

- 先确认 macOS 输出设备是 `MacBook Air扬声器` 或你的目标耳机 / 音箱。
- 启动 mock 模式后，对麦克风说一句话，让流程走完一轮。
- 如果扬声器工作正常，你应该能听到一段很短的提示音频；如果麦克风指示灯亮但完全没有任何播放反馈，优先检查 macOS 的输出设备与音量设置。

## Known Limits

- 当前只支持半双工打断设计，不支持真正全双工对话。
- 打断与 turn segmentation 目前仍是 MVP 级实现，阈值和分段策略还需要实机调优。
- 真实模式下仍依赖外部 ASR、LLM、TTS 服务可用。
- mock 模式主要用于本地端到端联调，回复质量不代表最终模型效果。

## Verification Status

- `python3 -m pytest -v`：测试覆盖 config、event bus、session store、adapter compatibility、mock backends、state machine、runtime orchestration、VAD、音频设备、self-test 与播放 fallback 行为。
- `python3 -m app.main`：真实设备模式可在本机正常启动。
- `PODCAST_BACKEND=mock python3 -m app.main`：mock 模式可在本机正常启动，并且 `Ctrl+C` 可干净退出。
- `PODCAST_BACKEND=mock PODCAST_SELF_TEST=1 python3 -m app.main`：会输出输入/输出设备、speech frame、ASR、TTS 与播放调用状态，便于快速诊断本地环境。
- `PODCAST_TEXT_DEMO="请先做一个简短的自我介绍" python3 -m app.main`：可在不启用麦克风的前提下直接验证 `LLM + TTS + 播放` 链路。
- `python3 -m mlx_audio.stt.generate --model mlx-community/Qwen3-ASR-0.6B-4bit --audio tmp/asr/sample.wav --output-path tmp/asr/sample.txt --format txt --language zh --verbose`：本机实测可完成中文转写，处理时间约 `1.95s`，峰值内存约 `1.37 GB`。
- `python3 -m mlx_audio.tts.generate --model mlx-community/Qwen3-TTS-12Hz-0.6B-Base-4bit --text "你好，我们现在在测试本地中文语音合成。" --output_path tmp/qwen3_tts --file_prefix qwen3_tts_test --audio_format wav --join_audio --verbose`：本机实测可生成中文 WAV，处理时间约 `6.02s`，峰值内存约 `3.97 GB`。
- 手工语音链路检查：代码层面已具备试跑条件，但真实 ASR / TTS 质量和本地模型部署表现仍需实机验证。

## Latency Notes

- `ASR final`：尚未测量。
- `LLM`：尚未测量。
- `TTS first-frame`：尚未测量。
- 当前 runtime 已经会打印每轮 `Turn latency`，并继续保留 ASR / LLM / TTS 的单段 timing 日志，便于后续做端到端 latency profiling。
- 下一阶段优先级是把这些 timing 汇总成更直观的 profiling 输出，并完成本地全链路稳定性验证。
当前默认 LLM 接口配置为：

```bash
LLM_BASE_URL=https://model-api.skyengine.com.cn/v1/chat/completions
LLM_MODEL=qwen3.5-flash
```

只要 `GEMINI_API_KEY` 里填入可用 Bearer token，runtime 就会按 OpenAI-compatible `chat/completions` 请求格式调用这个接口。
