# TTS 模型兼容性总体分析

## CosyVoice3 测试结果

**模型**: mlx-community/Fun-CosyVoice3-0.5B-2512-4bit  
**结果**: ❌ 不支持

```
ValueError: Model type cosyvoice3 not supported for tts.
```

**原因**: CosyVoice3 不在 mlx-audio 0.4.2 的支持列表中

---

## mlx-audio 支持的全部 TTS 模型

### 总体情况

**支持的模型总数**: 25 个

包括：
- bailingmm, bark, chatterbox, chatterbox_turbo, dense, dia
- echo_tts, fish_qwen3_omni, indextts, irodori_tts, kitten_tts
- **kokoro**, kugelaudio, llama, outetts, pocket_tts
- **qwen3**, **qwen3_tts**, sesame, soprano, spark
- tada, **vibevoice**, voxcpm, voxtral_tts

---

## 实际可用的模型

### ✅ 完全可用

1. **Qwen3-TTS** (推荐)
   - 模型: mlx-community/Qwen3-TTS-12Hz-0.6B-Base-4bit
   - 状态: ✅ 完美工作
   - 中文支持: 优秀
   - 延迟: 2-5 秒
   - 推荐指数: ⭐⭐⭐⭐⭐

2. **VibeVoice**
   - 模型: mlx-community/VibeVoice-Realtime-0.5B-4bit
   - 状态: ✅ 完美工作
   - 中文支持: 有（但自动检测不准）
   - 延迟: ~5 秒
   - 推荐指数: ⭐⭐

### ❌ 无法使用

1. **Kokoro** (所有变体)
   - ❌ 权重形状不匹配
   - 需要 PR #423 修复
   - 理论延迟: 100ms（如果能用的话）

2. **Bark**
   - ❌ 401 Client Error（认证问题）
   - 模型不可公开访问或已移除

3. **Echo-TTS**
   - ❌ 401 Client Error（认证问题）
   - 模型不可公开访问或已移除

4. **Fish-Qwen3-Omni**
   - ❌ 401 Client Error（认证问题）
   - 模型不可公开访问或已移除

5. **CosyVoice3** (新)
   - ❌ 模型类型不支持
   - 不在 mlx-audio 0.4.2 中实现
   - 需要后续版本才能支持

---

## 模型对比表

| 模型 | 状态 | 延迟 | 中文 | 推荐度 |
|-----|------|------|------|--------|
| **Qwen3-TTS** | ✅ 可用 | 2-5s | 优 | ⭐⭐⭐⭐⭐ |
| **VibeVoice** | ✅ 可用 | ~5s | 差 | ⭐⭐ |
| Kokoro | ❌ 损坏 | 快 | 有 | ⭐⭐⭐* |
| Bark | ❌ 无法访问 | ? | ? | ⭐ |
| Echo-TTS | ❌ 无法访问 | ? | ? | ⭐ |
| Fish-Qwen3-Omni | ❌ 无法访问 | ? | ? | ⭐ |
| CosyVoice3 | ❌ 不支持 | ? | ? | ⭐* |

*需要修复或版本更新

---

## 关键结论

### 1. 当前最优方案

**Qwen3-TTS 是唯一的现实选择**

理由：
- ✅ 完全可用
- ✅ 中文支持优秀
- ✅ 性能稳定
- ✅ 无需修复或等待
- ✅ 官方持续维护

### 2. 关于 CosyVoice3

- 这是一个新模型（可能很新）
- mlx-audio 0.4.2 中尚未支持
- 需要等待 mlx-audio 后续版本集成
- 或者需要自己实现适配器

### 3. 关于其他模型

- **Kokoro**: 等待 PR #423 合并
- **Bark, Echo-TTS, Fish-Qwen3-Omni**: 模型已下架或需要认证
- 这些都不是短期内可用的选项

---

## 建议

### 立即行动
- ✅ 继续使用 **Qwen3-TTS**（当前最优）
- ✅ 保持当前配置不变

### 持续监控
- 🔔 mlx-audio 官方更新（可能添加 CosyVoice3）
- 🔔 PR #423 进度（可能修复 Kokoro）
- 🔔 其他模型可用性恢复

### 不需要做
- ❌ 尝试使用不支持的模型
- ❌ 等待 CosyVoice3（会很久）
- ❌ 尝试其他有认证问题的模型

---

## 小结

在 **mlx-audio 0.4.2** 中：
- **实际可用**: 2 个模型（Qwen3-TTS, VibeVoice）
- **理论可用**: 1 个模型（Kokoro，需要修复）
- **未来可用**: 多个模型（需要版本更新或实现）
- **已下架**: 3+ 个模型（无法访问）

**当前最佳选择：Qwen3-TTS** ✅

继续使用它，定期检查更新即可！
