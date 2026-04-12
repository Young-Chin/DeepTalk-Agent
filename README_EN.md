<p align="center">
  <h1 align="center" style="color:#2E9EF7;">🎙️ DeepTalk Agent</h1>
  <p align="center">
    <b>Local Voice AI Assistant · Fully Offline</b>
  </p>
  <p align="center">
    English | <a href="README.md">中文</a>
  </p>
</p>

---

<p align="center">
  <a href="#-installation">Installation</a> •
  <a href="#%EF%B8%8F-configuration">Configuration</a> •
  <a href="#-launch">Launch</a> •
  <a href="#-architecture">Architecture</a>
</p>

## ✨ Introduction

Currently, this project is a local voice AI assistant that runs entirely on macOS using the MLX framework. It does not yet have agent capabilities. Future iterations will refine use cases and capabilities based on this foundation. 

> *While this is just a basic pipeline for me, it has complete functional workflows and an interactive interface. If this basic demo is helpful to you, feel free to star it.*

## 📦 Installation

```bash
git clone https://github.com/Young-Chin/DeepTalk-Agent.git
cd DeepTalk-Agent
uv sync
```

## 🖥️ Requirements

| Item | Requirement |
|------|-------------|
| System | macOS Apple Silicon (M1/M2/M3/M4) |
| Python | 3.10+ |
| Memory | 8GB+ |

## ⚙️ Configuration

```bash
cp .env.example .env
```

## 🚀 Launch

```bash
# 📟 CLI Mode
uv run python -m app.main

# 🌐 Web UI Mode (open http://localhost:8080)
uv run python run.py
```

**Controls:** Press `Space` to start recording → Press space again to end recording and send → Press space during playback to interrupt

## 🏗️ Architecture

```
🎤 Mic ──→ 📝 ASR ──→ 🧠 LLM ──→ 🔊 TTS ──→ 🔈 Speaker
            │                    │
            └── Local Offline ───┴── Supports Interruption
```

## 🎯 Models

| Component | Model | Size |
|:---------:|:-----:|:----:|
| 🎤 ASR | Qwen3-ASR-0.6B | ~500MB |
| 🧠 LLM | mlx-community/gemma-4-e2b-it-4bit | ~2GB |
| 🔊 TTS | mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-4bit | ~800MB |

Auto-downloaded on first run, then fully offline 🚀

## 🔧 Optional Configuration

<details>
<summary>📝 Settings</summary>

```bash
# TTS model switch (default: qwen3_custom with fixed voice)
MLX_TTS_MODEL_TYPE=qwen3_custom # kokoro / qwen3

# Speaker voice (qwen3_custom options: Vivian / Serena / Uncle_Fu / Dylan / Eric / Ryan)
MLX_TTS_VOICE=Serena

# TTS speed
MLX_TTS_SPEED=1.0

# Switch to remote LLM API (optional)
LLM_BACKEND=remote
GEMINI_API_KEY=your_api_key
```

</details>

## 📄 License

[Apache 2.0](LICENSE)


