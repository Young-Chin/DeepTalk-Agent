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

**错误**: `Expected shape (512, 3, 512) but received shape (512, 512, 3) for parameter predictor.F0.0.conv1.weight_v`

**原因**: Kokoro-82M-4bit 模型的权重张量布局与 MLX 0.31.1 + mlx-audio 0.4.2 不兼容。这是一个框架级别的兼容性问题，不能通过参数调整解决。

**当前状态**: 
- ✓ VibeVoice-Realtime-0.5B-4bit 正常工作
- ✓ Qwen3-TTS-12Hz-0.6B-Base-4bit 正常工作
- ✗ Kokoro-82M-4bit 不兼容（权重形状错误）

**解决方案**:
1. **推荐方案**: 使用 VibeVoice（平衡的延迟和质量）或 Qwen3（最佳质量）
   ```bash
   export MLX_TTS_MODEL_TYPE=vibevoice  # 推荐
   # 或
   export MLX_TTS_MODEL_TYPE=qwen3      # 最佳音质
   ```

2. **如果需要支持 Kokoro**，需要：
   - 升级 MLX 版本（>0.31.1）
   - 升级 mlx-audio 版本（>0.4.2）
   - 或使用不同的 Kokoro 模型版本

3. **清除缓存**（如果使用了旧的 modelscope 路径）:
   ```bash
   rm -rf ~/.cache/huggingface/hub/models--mlx-community--Kokoro*
   rm -rf ~/.cache/modelscope/hub/modelscope--Kokoro*
   ```

### VibeVoice 语言问题

**症状**: 输出音频是外语或听不懂的语言（即使输入是中文）

**原因**: VibeVoice 模型对多语言的支持有限制，自动语言检测不准确。模型可能倾向于识别为其他语言。

**当前状态**: 
- ✓ 模型加载成功
- ✓ 音频合成成功  
- ✗ 中文语言识别不正确

**解决方案**:
使用 Qwen3-TTS 替代（已验证支持中文）：
```bash
export MLX_TTS_MODEL_TYPE=qwen3  # 改为 Qwen3（推荐）
```

**备选方案**（如必须用 VibeVoice）:
1. 尝试添加语言提示前缀（如果模型支持）
2. 使用不同的 voice token
3. 等待模型更新

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

1. **使用 VibeVoice 模型** (平衡速度和质量，~5秒):
   ```bash
   export MLX_TTS_MODEL_TYPE=vibevoice  # 推荐
   ```

2. **提高语速**:
   ```bash
   export MLX_TTS_SPEED=1.2  # 1.0 为正常速度，1.2 为加速 20%
   ```

3. **缩短回复长度**:
   - 已优化 system prompt（≤50 字符，口语化、拟人化）
   - 限制 max_tokens=100

4. **注意**: Kokoro 模型当前与 MLX 0.31.1 不兼容，无法使用

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
