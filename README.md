# DeepTalk Agent CLI MVP

本项目是一个本地 CLI Demo，用来验证中文访谈播客的人机闭环：
麦克风输入 -> ASR -> 主持人式 LLM 回复 -> TTS 播放，并支持半双工打断。

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

- 当前输入设备
- 当前输出设备
- 当前播放模式（`real` 或 `memory`）
- 当前 ASR backend 会通过后续 ASR 结果间接体现；如果切到 `ASR_BACKEND=mlx`，这里走的是本地 MLX 推理
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
- `python3 -m mlx_audio.stt.generate --model mlx-community/Qwen3-ASR-0.6B-4bit --audio tmp/asr/sample.wav --output-path tmp/asr/sample.txt --format txt --language zh --verbose`：本机实测可完成中文转写，处理时间约 `1.95s`，峰值内存约 `1.37 GB`。
- 手工语音链路检查：代码层面已具备试跑条件，但真实 ASR / TTS 质量和本地模型部署表现仍需实机验证。

## Latency Notes

- `ASR final`：尚未测量。
- `LLM`：尚未测量。
- `TTS first-frame`：尚未测量。
- 当前阶段优先级仍是验证本地或外部 ASR / TTS 的真实效果，并根据机器性能选择合适模型与量化方案。
