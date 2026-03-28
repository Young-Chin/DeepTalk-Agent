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

启动后会进入一个最小 CLI 循环并保持运行，当前版本主要用于搭建链路骨架。

## Known Limits

- 当前只支持半双工打断设计，不支持真正全双工对话。
- 音频输入输出仍是 MVP 占位实现，后续会接入真实麦克风采集和播放链路。
- 运行依赖外部 ASR、LLM、TTS 服务可用。

## Verification Status

- `python3 -m pytest -v`：11 个测试全部通过，覆盖 config、event bus、session store、adapter contract、state machine 和 CLI bootstrap。
- `python3 -m app.main`：在本地 `.env` 存在时可成功启动并持续运行，已完成基础启动健检。
- 手工链路检查：尚未完成。当前音频输入输出仍为占位实现，因此还不能真实验证 ASR final、主持人口播、播放中断等端到端行为。

## Latency Notes

- `ASR final`：尚未测量。
- `LLM`：尚未测量。
- `TTS first-frame`：尚未测量。
- 当前阶段优先级仍是把真实音频采集、播放和中断链路接起来，再进行时延记录与调优。
