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
