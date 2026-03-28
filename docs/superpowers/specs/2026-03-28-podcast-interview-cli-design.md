# 人机访谈播客 Demo 设计（CLI / MVP）

日期：2026-03-28  
阶段：Design Spec（用于后续实现计划）  
目标：快速验证「ASR → Thinking → TTS」可行闭环，支持主持人式中文访谈与半双工打断。

## 1. 背景与目标

用户需要一个可自用的基础 Demo，用于验证：
- 受访者通过麦克风实时说话；
- 系统能理解并记录语义（ASR）；
- Agent 以主持人/采访者角色思考并回应（LLM）；
- 回应通过语音播报（TTS）；
- 播报中若受访者开口，系统立即停止播报并回到收音（半双工打断）。

本阶段只做 CLI 版本，优先“可体验、可迭代”，不追求产品级完整度。

## 2. 范围定义（MVP）

### 2.1 In Scope
- 运行形态：本地 CLI。
- 输入：麦克风实时音频（中文）。
- 对话模式：打断式实时对话（半双工）。
- 主持人风格：Agent 以采访者角色进行追问与回应。
- 会话记忆：内存级最近轮次上下文。
- 可观测性：基础日志与关键链路时延指标。

### 2.2 Out of Scope
- 全双工并讲（双向重叠发言）。
- 复杂回声消除、噪声抑制链路。
- 图形界面（Web/Electron）。
- 多人会话与长期持久化数据库。
- 复杂工作流编排与多代理协同。

## 3. 技术选型与约束

- ASR：Qwen3-ASR（通过 adapter 接入）。
- Agent Model：Gemini-3.1-pro（API 调用）。
- TTS：fish-speech（通过 adapter 接入）。
- 语言：中文优先（ASR/LLM/TTS 全中文链路）。
- 实现语言：Python（优先满足快速集成音频、网络与并发编排）。

## 4. 架构设计（方案 1：本地事件总线 + 分段流式管线）

在单进程中拆分模块，通过事件总线通信，降低耦合并保持可替换性。

### 4.1 核心模块
- `AudioIn`：麦克风采集与 VAD。
- `ASRClient`：音频分片转写，输出 partial/final 结果。
- `DialogueAgent`：管理访谈上下文，生成主持人回复文本。
- `TTSClient`：将文本转流式语音块。
- `AudioOut`：低延迟播放语音并支持立即 stop。
- `InterruptController`：在播报期监听打断并触发状态切换。
- `SessionStore`：维护内存态会话上下文。
- `MetricsLogger`：记录各阶段时延、错误、打断次数。

### 4.2 设计原则
- 事件驱动优先：模块通过事件解耦，不做硬依赖互调。
- 适配器边界清晰：ASR/LLM/TTS 统一接口，便于后续替换模型或服务。
- 实时性优先：先保证“可打断、可继续”，再迭代质量与表现。

## 5. 状态机与数据流

### 5.1 状态机（4 态）
1. `LISTENING`：持续收音与 VAD 检测。
2. `TRANSCRIBING`：对当前语段进行流式转写并等待 endpoint。
3. `THINKING`：调用 Gemini 生成主持人回复文本。
4. `SPEAKING`：调用 fish-speech 合成并播放语音。

### 5.2 主数据流
- 麦克风 PCM chunk → VAD → ASR partial/final
- ASR final + SessionStore 历史上下文 → Gemini response
- Gemini response → fish-speech stream → AudioOut playback

### 5.3 打断策略（半双工）
- `SPEAKING` 期间保留轻量 VAD 监听。
- 连续语音超过阈值（例如 200ms）触发 `INTERRUPT`。
- `AudioOut` 立即停止，清空待播缓冲，状态回到 `LISTENING`。
- 被打断的 Agent 输出标记为 interrupted，不计入“已完整播报内容”。

## 6. 目录结构（建议）

```text
app/
  main.py
  config.py
  bus.py
  state_machine.py
  audio/
    in_stream.py
    out_stream.py
  asr/
    qwen_adapter.py
  agent/
    gemini_adapter.py
  tts/
    fish_adapter.py
  memory/
    session_store.py
  observability/
    logger.py
requirements.txt
.env.example
README.md
```

## 7. 配置设计

`.env` 建议字段：
- `GEMINI_API_KEY`
- `QWEN_ASR_BASE_URL`
- `FISH_TTS_BASE_URL`
- `AUDIO_SAMPLE_RATE=16000`
- `VAD_START_MS=120`
- `VAD_INTERRUPT_MS=200`
- `TURN_SILENCE_MS=600`
- `LOG_LEVEL=INFO`

## 8. 错误处理与鲁棒性

- 各模块失败不导致主进程退出；回退至 `LISTENING`。
- ASR/LLM/TTS 各自具备轻量超时与重试（1~2 次）。
- 网络异常时给出可恢复日志，继续等待下一轮输入。
- 记录请求失败类型、阶段耗时、打断次数，支持后续性能优化。

## 9. 性能目标（MVP 级目标）

- 用户停顿到 ASR final：目标 `< 800ms`
- ASR final 到 Agent 首字生成：目标 `< 1200ms`
- Agent 文本到首帧播音：目标 `< 600ms`

说明：上述为调优目标值，用于迭代评估，不作为硬 SLA。

## 10. 验收标准（Demo）

满足以下条件即视为 MVP 可行：
- 可通过 CLI 启动并开始实时收音。
- 用户完成一轮发言后，Agent 能生成并语音播报主持人式回应。
- 播报中用户开口可触发即时停播并进入下一轮识别。
- 全链路日志可见（含每阶段耗时与错误原因）。
- 中文语义基本可理解，允许存在少量识别/表达误差。

## 11. 风险与后续迭代方向

### 11.1 主要风险
- 麦克风环境噪音导致 VAD 误触发或漏触发。
- 外部模型服务抖动导致响应时延波动。
- 打断阈值配置不当造成“误打断”或“打断不灵”。

### 11.2 后续优先迭代
1. 打断判定精细化（结合能量门限 + 关键词检测）。
2. 更稳健的 turn segmentation 与缓冲策略。
3. 会话记忆从内存升级为轻量持久化。
4. 增加可配置主持人风格模板与访谈主题设定。

## 12. 当前实现状态（2026-03-28）

- 已完成基础工程骨架：配置加载、事件总线、会话内存、adapter 契约、状态机、CLI 启动入口。
- 已完成自动化验证：当前测试套件覆盖核心骨架行为，最新本地结果为 11 个测试通过。
- 已完成启动健检：CLI 可在存在 `.env` 配置时启动并驻留。
- 尚未完成真实端到端链路：`AudioIn` / `AudioOut` 仍是占位实现，暂未接入麦克风、播放与半双工中断闭环。
- 因此，本文档第 10 节中的 Demo 验收标准目前只完成了“可启动、可观测基础骨架”的前置部分，尚未达到完整 MVP 可演示状态。
