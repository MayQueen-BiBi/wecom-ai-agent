# 系统架构（Architecture Freeze — Phase 1）

## 1. 系统目标

- **AI 客服**：企业微信场景下的自动应答与辅助。
- **多阶段 Agent**：按阶段编排（理解 → 状态更新 → 路由 → 执行 → 校验 → 回复）。
- **State-driven workflow**：单次回合以 `AgentRunState` 为单一可变载体；编排层按阶段读写状态（迁移期仍允许既有写法；**目标**为仅经 reducer 写入，见 `ARCHITECTURE_RULES.md`）。

---

## 2. 分层结构

### understanding

| 项 | 说明 |
|----|------|
| **职责** | 自然语言 → 结构化语义（intent、entities、rewritten_query、risk 等）。 |
| **输入** | 用户消息、可选上文（由 workflow 注入，不反向依赖 workflow）。 |
| **输出** | `UnderstandingResult`（及写入 state 的 reducer 输入）。 |
| **不允许** | 检索、路由决策、工具调用、直接生成对用户最终回复。 |

### routing

| 项 | 说明 |
|----|------|
| **职责** | 基于 **已填充** 的 state（尤其 risk、retrieval_score、clarify_count）决定 `route` / `action`。 |
| **输入** | `AgentRunState`（结构化字段）。 |
| **输出** | `PolicyEvaluationResult` 等价语义（action、rule_name、reason）及 trace 片段。 |
| **不允许** | LLM、检索、Prompt 生成、修改业务语义。 |

### workflow

| 项 | 说明 |
|----|------|
| **职责** | 节点顺序、条件分支、与 `StateMachine` / session 的衔接、调用各层 API。 |
| **输入** | 用户 id、消息、外部依赖（session、cache）。 |
| **输出** | 对用户可见回复及可观测 trace。 |
| **不允许** | 实现检索细节、拼接执行侧 Prompt、实现工具协议（应委托 execution / services）。 |

### execution

| 项 | 说明 |
|----|------|
| **职责** | 检索、合并 query、LLM 生成、工具调用、后处理；按 `state.action` 分发。 |
| **输入** | `AgentRunState`、`StateMachine`、配置。 |
| **输出** | 更新后的 state 片段（目标经 reducer）、副作用（会话写入、缓存）在边界外显式发生。 |
| **不允许** | 作为唯一来源做 NL 意图理解、决定路由（路由归 routing）。 |

### critic

| 项 | 说明 |
|----|------|
| **职责** | 对 **草稿** 做清单式校验（规则见 `critic_rules`）。 |
| **输入** | 从 state 抽取的只读上下文 + 草稿文本。 |
| **输出** | 通过/修订文本及 trace（**目标**：仅 `List[CriticIssue]`，见 `ARCHITECTURE_RULES.md`）。 |
| **不允许** | 修改 `AgentRunState` 业务字段（当前实现以修订文本为主；冻结后逐步收敛）。 |

### state

| 项 | 说明 |
|----|------|
| **职责** | 回合态、会话存储类型与默认实例；**纯** reducer 写入规范化（`reducers.py`）。 |
| **输入** | reducer 的旧 state + 各阶段 result。 |
| **输出** | 新 `AgentRunState` 实例（不可变更新风格）。 |
| **不允许** | 发起 IO、调用 LLM（会话 store 的 IO 在 workflow / execution 边界显式调用）。 |

### services

| 项 | 说明 |
|----|------|
| **职责** | 预约、数据库等与领域持久化相关的服务。 |
| **输入** | 工具参数 / 查询。 |
| **输出** | 业务结果。 |
| **不允许** | 依赖 workflow 或编排层（避免反向依赖）。 |

### observability

| 项 | 说明 |
|----|------|
| **职责** | 日志、trace、指标、FlowTracker。 |
| **输入** | 各层传入的结构化事件。 |
| **输出** | 日志与聚合指标。 |
| **不允许** | 修改对话业务状态（只读或旁路写入指标存储）。 |

---

## 3. 单向依赖图

```text
workflow
  ↓
understanding / routing / execution / critic
  ↓
services / core（基础设施与共享能力）
```

禁止：understanding → workflow；routing → LLM；critic → session_store 等反向依赖（细则见 `DEPENDENCY_RULES.md`）。

---

## 4. 状态流转

```text
User Input
  → Understanding
  → State Update（目标：经 reducer）
  → Routing
  → Execution（检索 / 生成 / 工具）
  → Critic
  → Response
```

---

## 5. 相关文档

| 文件 | 内容 |
|------|------|
| `ARCHITECTURE_RULES.md` | 硬规则（边界、state、Prompt 位置）。 |
| `DEPENDENCY_RULES.md` | 允许 / 禁止依赖矩阵。 |
| `DIRECTORY.md`（仓库根） | 物理目录树说明。 |
