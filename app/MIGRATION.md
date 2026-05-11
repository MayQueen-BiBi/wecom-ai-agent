# 目录迁移进度

## Phase 1（完成）

| 新位置 | 内容 |
|--------|------|
| `app/state/` | `AgentRunState`、`session_store`（Redis/内存）、`types.AgentStateLayered` |
| `app/observability/` | `configure_logging`、`FlowTracker`、`RequestTrace`、`get_metrics` / `update_metrics` |

兼容 shim（过渡期可删）：

- `app/logging_config.py` → 转发 `app.observability.logging_config`

> **Phase 7**：`app/agent` 已删除；入口见 `app/api/entry.py`，编排见 `app/workflows/`。

## 已移除的遗留代码

- **`app/agent/session.py`**（`Session` / 进程内 `sessions` / `get_session` 等）已删除：未接入主链路，且与 Policy-Driven 架构（`workflow`、`AgentRunState`、`session_store`、StateMachine）重复。不再提供兼容层。

## 状态边界约定（后续 Phase）

- **`app/state/`**：回合态、策略计数持久化（如 `AgentRunState`、`session_store`）
- **`app/runtime/`**：（待建）进程内运行时单例、worker 级资源
- **`app/workflows/`**：（待建）编排入口
- **`app/memory/`**：（待建）长期记忆 / 外部记忆适配

禁止再以「Session 超级容器」聚合业务状态。

## 后续 Phase（计划）

- Phase 2：`app/understanding/`（intent_classifier、extraction、prompt_templates、unified_understanding）
- Phase 3：`app/routing/`（routing_policy、risk_guard、retrieval_guard）
- Phase 4：`app/execution/`
- Phase 5：`app/workflows/`、`app/orchestrator/`
