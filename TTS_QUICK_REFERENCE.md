# TTS 快速参考指南

## 三个核心问题 Quick Answer

### Q1: Kokoro 版本能否升级？
```
A: 需要测试后才知道。风险和收益都有可能。

风险: Qwen3/VibeVoice 可能不兼容
收益: Kokoro 可能变得可用

推荐: 先备份，升级后运行完整测试
```

### Q2: VibeVoice 中文输出非中文，是配置问题吗？
```
A: 不完全是。核心问题：VibeVoice 不支持 lang_code 参数。

原因：
- VibeVoice 使用"自动语言检测"
- 自动检测对中文识别不准（这是模型训练问题）
- 无法强制指定语言

解决方案：
1. 改用 Qwen3-TTS（强烈推荐）✓
2. 保留 VibeVoice 作为备选，接受其局限性
3. 等待 VibeVoice 后续版本改进
```

### Q3: 有离线测试的 case 吗？
```
A: 有！已创建完整框架。

工具列表：
1. test_tts_models.py           - 基础测试
2. test_tts_comprehensive.py    - 综合测试（新增）
3. diagnose_vibevoice_language.py - 诊断工具（新增）

全部支持多语言、多长度文本、自动生成可播放的 WAV
```

---

## 快速命令

### 运行测试

```bash
# 测试 Qwen3（推荐，最快）
python3 -m app.tests.test_tts_models --model-type qwen3

# 所有模型对比
python3 -m app.tests.test_tts_models --compare

# 综合测试（新）
python3 -m app.tests.test_tts_comprehensive --all --diagnose

# VibeVoice 诊断（新）
python3 -m app.tests.diagnose_vibevoice_language
```

### 升级 MLX（用于测试 Kokoro）

```bash
# 步骤 1: 备份
pip freeze > requirements_backup.txt

# 步骤 2: 升级
pip install --upgrade mlx mlx-audio

# 步骤 3: 测试
python3 -m app.tests.test_tts_comprehensive --model kokoro

# 步骤 4: 如果失败则恢复
pip install -r requirements_backup.txt
```

### 检查版本

```bash
pip list | grep -E "^(mlx|mlx-audio)" | awk '{print $1, $2}'
```

---

## 测试输出文件位置

```
tests/
├── output/
│   ├── tts_test_*.wav           # 基础测试输出
│   ├── test_report_*.json       # 综合测试报告
│   └── vibevoice_diagnosis/     # VibeVoice 诊断文件
│       ├── vibevoice_chinese_*.wav
│       ├── vibevoice_english_*.wav
│       └── vibevoice_mixed_*.wav
```

---

## 性能参考

### Qwen3-TTS 实测延迟

| 文本长度 | 字数 | 耗时 | 文件大小 |
|--------|------|------|--------|
| 短文本 | 2字 | 3.1s | 64KB |
| 中文本 | 12字 | 2.3s | 142KB |
| 长文本 | 40字 | 5.2s | 375KB |
| 英文短 | 5字 | 1.8s | 26KB |
| 英文中 | 40字 | 2.0s | 135KB |

**总体评价：** 延迟可控，质量稳定，中文支持优秀

---

## 常见问题排查

### 问题：升级后 Qwen3 停止工作
```
原因：版本不兼容
方案：恢复 requirements_backup.txt
```

### 问题：VibeVoice 发音不对
```
原因：模型设计限制
方案：改用 Qwen3-TTS（即时解决）
     或运行诊断了解具体情况
```

### 问题：Kokoro 仍然不工作
```
原因：版本问题仍未解决
方案：1. 检查升级是否成功
     2. 查看详细错误日志
     3. 考虑放弃 Kokoro，继续用 Qwen3
```

### 问题：测试生成的 WAV 没有声音
```
原因：可能音频编码问题
方案：1. 检查文件大小（应 > 1KB）
     2. 尝试用不同播放器打开
     3. 检查日志中的 sample_rate
```

---

## 推荐配置

### `.env` 最终推荐

```env
# TTS 配置
TTS_BACKEND=mlx_qwen3
MLX_TTS_MODEL_TYPE=qwen3

# 模型路径
MLX_TTS_QWEN3_MODEL=mlx-community/Qwen3-TTS-12Hz-0.6B-Base-4bit

# （可选）保留备用模型配置
MLX_TTS_VIBEVOICE_MODEL=mlx-community/VibeVoice-Realtime-0.5B-4bit
MLX_TTS_KOKORO_MODEL=mlx-community/Kokoro-82M-4bit

# 语言和参数
MLX_TTS_LANGUAGE=zh
MLX_TTS_SPEED=1.0
```

---

## 下一步工作

### 如果要优化速度
- 调整 `MLX_TTS_SPEED` 参数（0.5-2.0）
- 批量处理文本
- 预热模型（首次加载较慢）

### 如果要测试其他模型
- 修改 `.env` 中的 `MLX_TTS_MODEL_TYPE`
- 运行测试套件
- 对比性能

### 如果要自动化测试
- 使用 `--save-report` 生成 JSON
- 集成到 CI/CD pipeline
- 定期运行基准测试

---

## 关键要点

✓ **Qwen3-TTS** 是当前最佳选择  
⚠️ **VibeVoice** 已知中文检测问题，非配置问题  
🔄 **Kokoro** 需要版本升级，尚未确认可行性  
📊 **测试工具** 已完整搭建，即插即用
