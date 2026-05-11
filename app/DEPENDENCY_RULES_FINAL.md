# 依赖规则 FINAL（Phase 7）

## FINAL RULES

- **No module under `app/` may import `app.agent`.**  
  The legacy `app/agent` package has been **removed**. All runtime goes through explicit layers below.

- **HTTP / 集成入口** 必须经 **`app/api/entry.py`**：异步 **`handle_request(AgentRequest) -> AgentResponse`**（契约版本见 **`app.api.protocol.CONTRACT_VERSION`**）；同步测试可用 **`invoke_request`**。不得绕开协议类型。

- **`app/workflows/`** 是 **唯一编排层**（Graph + nodes）。

- **`app/execution/`** 保持 **纯执行**（state + action → `ExecutionResult`，不经由已删除的 agent）。

- **`app/state/`** 以 **reducer** 为写回契约；执行器不直连 session 等副作用（由 workflow 收口）。

## 校验

```bash
python scripts/check_dependency.py
```

实现：`app/guards/dependency_guard.py`（`check_dependency_graph() -> bool`）。

## 与 V2 / V1

* `app/DEPENDENCY_RULES_V2.md`：Phase 5–6 演进说明（白名单阶段已结束）。
* `app/DEPENDENCY_RULES.md`：历史分层示例。

**以本文为 Phase 7 后的最终约束。**
