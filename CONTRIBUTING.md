# Contributing to DeepTalk Agent

Thank you for your interest in contributing to DeepTalk Agent! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## How to Contribute

### Reporting Bugs

If you find a bug, please create an issue with:

1. A clear title describing the problem
2. Steps to reproduce the issue
3. Expected behavior
4. Actual behavior
5. Your environment (OS, Python version, etc.)

### Suggesting Features

Feature suggestions are welcome! Please create an issue with:

1. A clear title describing the feature
2. A detailed description of the proposed feature
3. Any relevant examples or use cases

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests to ensure everything works
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to your branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Development Setup

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/)
- Node.js 18+ (for frontend development)

### Setup

```bash
# Clone your fork
git clone https://github.com/Young-Chin/DeepTalk-Agent.git
cd DeepTalk-Agent

# Install dependencies
uv sync

# Install frontend dependencies
cd frontend && npm install && cd ..

# Create .env file
cp .env.example .env
# Edit .env with your API keys

# Activate virtual environment
source .venv/bin/activate
```

## Running Tests

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_config.py
```

## Code Style

- Follow PEP 8 guidelines
- Use type hints where appropriate
- Write docstrings for public functions and classes
- Keep line length under 100 characters

### Type Checking

```bash
# If you use mypy
mypy app/
```

## Project Structure

```
DeepTalk-Agent/
├── app/                    # Main application
│   ├── agent/             # AI agent implementation
│   ├── asr/               # Automatic Speech Recognition
│   ├── audio/             # Audio capture and playback
│   ├── memory/            # Conversation memory
│   ├── mocks/             # Mock implementations for testing
│   ├── observability/     # Logging and monitoring
│   ├── tests/             # Internal tests
│   ├── tts/               # Text-to-Speech
│   ├── config.py          # Configuration management
│   ├── main.py            # CLI entry point
│   ├── server.py          # Web server entry point
│   └── websocket_handler.py
├── frontend/              # React Web UI
│   ├── src/              # Frontend source code
│   └── package.json
├── tests/                 # Integration tests
├── pyproject.toml         # Project configuration and dependencies
└── .env.example           # Example environment variables
```

## Adding New Features

### Adding a New ASR Backend

1. Create a new file in `app/asr/` implementing the `ASRAdapter` interface
2. Add configuration options to `app/config.py`
3. Update the factory to support your backend
4. Add tests in `tests/`

### Adding a New TTS Backend

1. Create a new file in `app/tts/` implementing the `TTSAdapter` interface
2. Add configuration options to `app/config.py`
3. Update the factory to support your backend
4. Add tests in `tests/`

### Adding a New LLM Backend

1. Create a new file in `app/agent/` implementing the LLM interface
2. Add configuration options to `app/config.py`
3. Update the agent to support your backend
4. Add tests in `tests/`

## Commit Messages

- Use clear and descriptive commit messages
- Start with a type: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`
- Keep the first line under 72 characters

Examples:
- `feat: add support for OpenAI Whisper ASR`
- `fix: resolve audio device selection on Linux`
- `docs: update installation instructions`

## Questions?

Feel free to open an issue for any questions about contributing!

Thank you for contributing to DeepTalk Agent!
