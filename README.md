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

## Run

```bash
python3 -m app.main
```

启动后会进入实时音频循环并持续等待语音输入。

## Mock Mode

在本地 ASR / TTS 服务还没部署完成前，可以先用 mock backend 跑通完整链路：

```bash
PODCAST_BACKEND=mock python3 -m app.main
```

mock 模式下：

- 麦克风和本地播放仍然使用真实音频设备。
- ASR / 主持人回复 / TTS 使用内置 mock backend。
- 不需要配置 `GEMINI_API_KEY`、`QWEN_ASR_BASE_URL`、`FISH_TTS_BASE_URL`。

## Known Limits

- 当前只支持半双工打断设计，不支持真正全双工对话。
- 打断与 turn segmentation 目前仍是 MVP 级实现，阈值和分段策略还需要实机调优。
- 真实模式下仍依赖外部 ASR、LLM、TTS 服务可用。
- mock 模式主要用于本地端到端联调，回复质量不代表最终模型效果。

## Verification Status

- `python3 -m pytest -v`：56 个测试全部通过，覆盖 config、event bus、session store、adapter compatibility、mock backends、state machine、runtime orchestration、VAD、音频设备与播放格式处理。
- `python3 -m app.main`：真实设备模式可在本机正常启动。
- `PODCAST_BACKEND=mock python3 -m app.main`：mock 模式可在本机正常启动，并且 `Ctrl+C` 可干净退出。
- 手工语音链路检查：代码层面已具备试跑条件，但真实 ASR / TTS 质量和本地模型部署表现仍需实机验证。

## Latency Notes

- `ASR final`：尚未测量。
- `LLM`：尚未测量。
- `TTS first-frame`：尚未测量。
- 当前阶段优先级仍是验证本地或外部 ASR / TTS 的真实效果，并根据机器性能选择合适模型与量化方案。
