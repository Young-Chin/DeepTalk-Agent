# TTS 模型调试指南

## 快速开始

### 1. 运行日志系统

所有详细日志保存在 `logs/run.log`，包含：
- 模型加载信息
- TTS 合成参数
- 错误详情和堆栈跟踪
- 性能指标（延迟、大小等）

```bash
# 查看最新日志
tail -f logs/run.log

# 查看错误日志
grep ERROR logs/run.log

# 查看 TTS 相关日志
grep "TTS" logs/run.log
```

### 2. TTS 模型测试工具

使用测试工具验证各个模型：

```bash
# 测试单个模型
python3 -m app.tests.test_tts_models --model-type kokoro --verbose

# 测试所有模型并对比
python3 -m app.tests.test_tts_models --compare

# 自定义测试文本
python3 -m app.tests.test_tts_models --model-type vibevoice \
  --text="你好，欢迎参加这次访谈"

# 保存输出到指定文件
python3 -m app.tests.test_tts_models --model-type qwen3 \
  --output=output.wav
```

## 已知问题与解决方案

### Kokoro 模型问题

**错误**: `shape (512, 3, 512) but received shape (512, 512, 3)`

**原因**: Kokoro 模型的权重布局与其他模型不同，需要特殊的参数处理。

**解决方案**:
1. 已自动检测 Kokoro 模型并使用 `lang` 参数而非 `lang_code`
2. 如果仍然报错，尝试：
   ```bash
   # 清除模型缓存，重新下载
   rm -rf ~/.cache/modelscope/hub/modelscope--Kokoro-82M-4bit
   export MLX_TTS_MODEL_TYPE=kokoro
   python3 -m app.tests.test_tts_models --model-type kokoro --verbose
   ```

### VibeVoice 语言问题

**症状**: 输出音频是外语或听不懂的语言

**原因**: 语言代码传递错误或模型配置不当

**解决方案**:
1. 检查语言配置：
   ```bash
   export MLX_TTS_LANGUAGE=zh  # 确保设置为中文
   ```

2. 验证模型参数（查看详细日志）:
   ```bash
   export LOG_LEVEL=DEBUG
   python3 -m app.main
   grep "TTS 生成参数" logs/run.log
   ```

3. 如果问题依然存在，尝试重置模型:
   ```bash
   # 清除缓存
   rm -rf ~/.cache/modelscope/hub/modelscope--VibeVoice*
   
   # 重新测试
   python3 -m app.tests.test_tts_models --model-type vibevoice --verbose
   ```

## 调试流程

### Step 1: 基础测试

```bash
# 使用短文本快速测试
python3 -m app.tests.test_tts_models --model-type vibevoice \
  --text="你好" --verbose
```

### Step 2: 查看详细日志

```bash
# 启用 DEBUG 级别日志
export LOG_LEVEL=DEBUG

# 运行测试
python3 -m app.tests.test_tts_models --model-type vibevoice

# 查看日志
tail -100 logs/run.log
```

### Step 3: 分析问题

在日志中查找以下关键信息：

```
# 模型加载
Loading TTS model: modelscope/VibeVoice-Realtime-0.5B-4bit
TTS model loaded successfully

# TTS 合成参数
TTS 生成参数：model=VibeVoice-Realtime-0.5B-4bit, lang=zh, voice=None

# 错误信息（如果有）
TTS 合成失败：<错误信息>
错误类型：<错误类型>
```

### Step 4: 提交 Bug 报告

如果遇到问题，收集以下信息：

```bash
# 1. 系统信息
python3 -c "import platform; print(platform.platform())"
python3 -c "import mlx; print('MLX:', mlx.__version__ if hasattr(mlx, '__version__') else 'unknown')"
python3 -c "import mlx_audio; print('MLX Audio:', 'installed')"

# 2. 日志文件
cat logs/run.log > bug_report.log

# 3. 测试输出
python3 -m app.tests.test_tts_models --model-type <your_model> --verbose 2>&1 | tee test_output.txt
```

## 性能优化建议

### 降低延迟

1. **使用 Kokoro 模型** (最快):
   ```bash
   export MLX_TTS_MODEL_TYPE=kokoro
   ```

2. **提高语速**:
   ```bash
   export MLX_TTS_SPEED=1.2  # 1.0 为正常速度
   ```

3. **缩短回复长度**:
   - 已优化 system prompt
   - 限制 max_tokens=100

### 提高音质

1. **使用 Qwen3 模型** (最佳音质):
   ```bash
   export MLX_TTS_MODEL_TYPE=qwen3
   ```

2. **增加 diffusion steps** (如果支持):
   ```python
   # 修改 qwen_adapter.py 中的 generate 调用
   kwargs["ddpm_steps"] = 50  # 默认 20，增加到 50
   ```

## 日志示例

### 成功的 TTS 合成日志

```
2026-04-02 00:45:23 INFO podcast.tts.mlx ============================================================
2026-04-02 00:45:23 INFO podcast.tts.mlx 开始 TTS 合成
2026-04-02 00:45:23 INFO podcast.tts.mlx   文本长度：15 字符
2026-04-02 00:45:23 INFO podcast.tts.mlx   模型：VibeVoice-Realtime-0.5B-4bit
2026-04-02 00:45:23 INFO podcast.tts.mlx   语言：zh
2026-04-02 00:45:23 INFO podcast.tts.mlx   语速：1.000000
2026-04-02 00:45:23 DEBUG podcast.tts.mlx TTS 生成参数：model=VibeVoice-Realtime-0.5B-4bit, lang=zh, voice=None
2026-04-02 00:45:24 INFO podcast.tts.mlx TTS 合成完成
2026-04-02 00:45:24 INFO podcast.tts.mlx   音频大小：125.3 KB
2026-04-02 00:45:24 INFO podcast.tts.mlx ============================================================
```

### 失败的 TTS 合成日志

```
2026-04-02 00:45:23 ERROR podcast.tts.mlx TTS 合成失败：Expected shape (512, 3, 512) but received shape (512, 512, 3)
2026-04-02 00:45:23 ERROR podcast.tts.mlx   错误类型：ValueError
2026-04-02 00:45:23 DEBUG podcast.tts.mlx 堆栈跟踪:
Traceback (most recent call last):
  ...
```

## 联系与支持

遇到问题？请提供：
1. `logs/run.log` 完整日志
2. 测试输出 (`test_output.txt`)
3. 系统信息
4. 复现步骤
