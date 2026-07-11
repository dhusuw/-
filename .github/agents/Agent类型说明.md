# ReAct 模式详解

> 2022年Google Research与Princeton联合提出 | 论文：*ReAct: Synergizing Reasoning and Acting in Language Models*

---

## 一、定义

ReAct = **Re**asoning + **Act**ing。将LLM的**推理能力**与**工具调用能力**交织为一个循环，让模型不再是"想好了再答"，而是"边想边做、边做边调整"。

核心思想一句话：**把思考链（Chain-of-Thought）和行动（Action）交织在一起，每一步推理后都可以调用外部工具获取真实信息，再基于工具返回的结果继续推理。**

---

## 二、核心循环

```
┌──────────────────────────────────────────────────┐
│                                                  │
│   Thought ──→ Action ──→ Observation             │
│       ↑                      │                   │
│       └──────────────────────┘                   │
│                                                  │
│   循环直到：Final Answer                          │
└──────────────────────────────────────────────────┘
```

### 三个组件

| 组件 | 内容 | 例子 |
|------|------|------|
| **Thought（思考）** | 分析当前状态、决定下一步、评估已有信息是否足够 | "我需要先查当前汇率，再计算兑换金额。" |
| **Action（行动）** | 调用工具，从预定义的工具集中选择 | `WebSearch("USD to CNY exchange rate 2026-07")` |
| **Observation（观察）** | 工具返回的结果，成为下一轮思考的输入 | `返回：1 USD = 7.25 CNY` |

### 详细循环流程

```
第1轮：
  Thought:  用户问美元兑人民币汇率，我不知道最新数据，需要搜索
  Action:   WebSearch("美元兑人民币汇率 2026年7月")
  Observation: 1 USD = 7.25 CNY

第2轮：
  Thought:  拿到汇率了。用户想问100美元等于多少人民币
  Action:   Calculator("100 * 7.25")
  Observation: 725

第3轮：
  Thought:  计算完成，汇率+计算结果都有，可以回答了
  Final Answer: 当前1美元=7.25人民币，100美元=725人民币
```

---

## 三、与纯推理模式的对比

### Chain-of-Thought (CoT) —— 纯推理

```
用户："苹果3块一个，买5个，付20，找多少钱？"

CoT输出：
  苹果单价3元，买5个：3×5=15元
  付了20元：20-15=5元
  答案：找5元

问题：所有知识来自训练数据，无法获取外部信息。
      如果问"今天的苹果实时价格"，CoT就会编造。
```

### ReAct —— 推理+行动交织

```
用户："苹果公司今天股价多少？"

ReAct输出：
  Thought: 需要实时股价数据，搜索
  Action:  WebSearch("AAPL stock price today")
  Observation: $198.73

  Thought: 拿到数据了，可以回答
  Final Answer: Apple今天股价$198.73
```

### 对比表

| 维度 | 纯LLM | CoT | ReAct |
|------|-------|-----|-------|
| 推理能力 | ✗ | ✓ | ✓ |
| 获取外部信息 | ✗ | ✗ | ✓ |
| 可追溯性 | ✗ | 部分 | ✓（每一步可见） |
| 自我纠错 | ✗ | ✗ | ✓ |
| 幻觉率 | 高 | 中 | 低（工具返回事实约束） |
| 适用场景 | 简单对话 | 数学/逻辑推理 | 复杂多步任务、实时信息需求 |

---

## 四、论文核心发现

ReAct论文的三个关键结论：

### 1. 事实性显著提升
在HotpotQA（多跳推理问答）上，ReAct的F1得分比纯CoT高**15%以上**。原因是工具调用（维基百科搜索）提供了事实锚点，阻止推理漂移。

### 2. 可解释性大幅增强
每一步Thought+Action+Observation都是可读的自然语言。人类可以逐行追踪——"为什么这个答案是对的？"不再黑箱。

### 3. 推理-行动互补
- 纯推理（CoT）在数学/逻辑题上更强，但遇到需要外部信息时不可靠
- 纯行动（Action-only）更快，但缺少规划，容易乱找
- **ReAct结合两者**：推理指导行动方向，行动提供推理所需的事实依据

---

## 五、ReAct的衍生模式

| 模式 | 论文/年份 | 改进点 |
|------|----------|--------|
| **ReAct** | Google, 2022 | 基础版：Thought→Action→Observation循环 |
| **Reflexion** | Shinn et al., 2023 | ReAct + 自我反思：执行失败后生成反思文本存入长期记忆，下一轮参考 |
| **Plan-and-Solve** | Wang et al., 2023 | 先写完整计划再逐步执行，减少中间步骤的短视 |
| **Tree-of-Thoughts (ToT)** | Yao et al., 2023 | 多分支并行探索，BFS/DFS搜索思考树，剪枝后选最优 |
| **ReWOO** | Xu et al., 2023 | 分离推理和行动：先一次性规划所有工具调用，再批量执行，减少LLM调用次数 |
| **RAISE** | 2023 | ReAct + 记忆增强：在循环中加入短期/长期记忆检索 |
| **ADaPT** | 2023 | 动态决策：LLM自主判断下一步用推理还是行动 |

---

## 六、从ReAct到Agent

ReAct是**单次会话内**的推理-行动循环。完整的Agent架构在此基础上加了三层：

```
ReAct（核心引擎）
    │
    ├─ + 长期记忆（向量数据库/知识图谱）
    │      → 跨会话的知识积累
    │
    ├─ + 多Agent协作
    │      → 多个ReAct实例并行，互相派任务
    │
    └─ + 安全护栏（Guardrails）
           → 关键行动前的人类审批、规则检查
```

### Claude Code中的对应

| ReAct组件 | Claude Code实现 |
|-----------|----------------|
| Thought | 模型内部推理（think标签内） |
| Action | 工具调用：Read/Write/Bash/WebSearch/Agent |
| Observation | 工具返回结果/错误信息 |
| 循环控制 | 直到输出最终回复给用户 |
| 长期记忆 | MEMORY.md + Memory目录 |
| 多Agent | Agent工具派生子Agent（也是ReAct实例） |

---

## 七、Prompt模板示例

实际实现ReAct时使用的典型System Prompt结构：

```
You run in a loop of Thought, Action, Observation.
Use Thought to reason about the current situation.
Use Action to run one of the available tools.
Observation will be the result of running that tool.
Repeat Thought → Action → Observation until you can
produce the Final Answer.

Available tools:
- WebSearch(query: string): search the web
- Calculator(expression: string): evaluate math
- Read(file_path: string): read a file

Always output in this format:

Thought: <your reasoning>
Action: ToolName({"param": "value"})
```

---

## 八、局限性

| 问题 | 说明 |
|------|------|
| **Token消耗高** | 每一步Thought+Action+Observation都计入上下文，长任务可能耗尽窗口 |
| **步数膨胀** | 简单问题也可能被拆成过多步骤，延迟增加 |
| **工具依赖** | 工具描述不准确或结果质量差时，链式错误放大 |
| **缺乏长期规划** | 单步推理容易陷入局部最优，丢失全局目标 |
| **确定性差** | 同一问题两次运行可能走不同路径，结果不一致 |

---

## 九、总结

ReAct是目前**所有AI Agent的底层发动机**。它解决了LLM的两个核心缺陷：
1. **不知道的事不会去查** → 工具调用赋予获取外部信息的能力
2. **错了不会改** → 观察结果反馈进下一轮思考，形成修正回路

2026年的Agent框架（LangGraph、CrewAI、AutoGen）本质上都在ReAct之上做了**编排、记忆、协作**的扩展，但循环内核没变。
