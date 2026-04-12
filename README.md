<p align="center">
  <h1 align="center" style="color:#2E9EF7;">🎙️ DeepTalk Agent</h1>
  <p align="center">
    <b>本地语音 AI 助手 · 完全离线运行</b>
  </p>
  <p align="center">
    <a href="README_EN.md">English</a> | 中文
  </p>
</p>

<p align="center">
  <a href="#-安装">安装</a> •
  <a href="#%EF%B8%8F-配置">配置</a> •
  <a href="#-启动">启动</a> •
  <a href="#-架构">架构</a>
</p>

---

## ✨ 介绍

目前该项目版本仅仅是一个本地语音对话助手，完全基于MLX框架运行在MacOS上，还不具备agent能力。未来会基于此进一步细化使用场景和能力，目前正在致力于平衡agent能力与时延。

>*虽然对我而言这只是一个基础pipe，但是具备完整的功能流程和交互界面，如果这个基础demo对你有帮助，欢迎star。*


## 📦 安装

```bash
git clone https://github.com/Young-Chin/DeepTalk-Agent.git
cd DeepTalk-Agent
uv sync
```

## 🖥️ 环境要求

| 项目 | 要求 |
|------|------|
| 系统 | macOS Apple Silicon (M1/M2/M3/M4) |
| Python | 3.10+ |
| 内存 | 8GB+ |

## ⚙️ 配置

```bash
cp .env.example .env
```

## 🚀 启动

```bash
# 📟 CLI 模式
uv run python -m app.main

# 🌐 Web UI 模式（访问 http://localhost:8080）
uv run python run.py
```

**操作：** 按 `空格` 开始录制 → 再按空格结束录制并发送 → 播放时按空格打断

## 🏗️ 架构

```
🎤 Mic ──→ 📝 ASR ──→ 🧠 LLM ──→ 🔊 TTS ──→ 🔈 Speaker
            │                    │
            └── 本地离线 ─────────┴── 支持打断
```

## 🎯 本地模型

| 组件 | 模型 | 大小 |
|:----:|:----:|:----:|
| 🎤 ASR | Qwen3-ASR-0.6B | ~500MB |
| 🧠 LLM | mlx-community/gemma-4-e2b-it-4bit | ~2GB |
| 🔊 TTS | mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-4bit | ~800MB |

首次运行自动下载，之后完全离线 🚀

## 🔧 可选配置

<details>
<summary>📝 配置项</summary>

```bash
# TTS 模型切换（默认 qwen3_custom，支持固定音色）
MLX_TTS_MODEL_TYPE=qwen3_custom # kokoro / qwen3

# 指定音色（qwen3_custom 可选：Vivian / Serena / Uncle_Fu / Dylan / Eric / Ryan）
MLX_TTS_VOICE=Serena

# TTS 语速
MLX_TTS_SPEED=1.0

# 切换远程 LLM API (可选)
LLM_BACKEND=remote
GEMINI_API_KEY=your_api_key
```

</details>

## 📄 License

[Apache 2.0](LICENSE)

---


