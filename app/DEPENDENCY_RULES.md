# 依赖规则（Dependency Rules）

## 允许依赖（示例）

```text
workflow        → understanding
workflow        → routing
workflow        → execution（`app.execution.dental_execution_layer`）
workflow        → critic_rules
workflow        → state
workflow        → observability

execution       → services
execution       → state（只读或可经 reducer 写入）
execution       → understanding（仅执行侧允许的模板/工具函数，禁止 NL 再理解）

understanding   → config
routing         → config（如未来需要路径配置）
critic_rules    → state（只读抽取字段；禁止写回 session_store）
```

## 禁止依赖（示例）

```text
understanding   → workflow
understanding   → execution
understanding   → routing

routing         → llm_client / 任意 LLM
routing         → rag_enhanced / retrieval

critic_rules    → session_store（不得直接改会话）
critic_rules    → workflow

services        → workflow
services        → dental_v3.workflow

observability   → state_machine（避免指标反推业务状态机）
```

## 说明

- **「禁止」**指默认不允许的新增 import / 运行时调用；存量兼容路径不在本阶段物理删除。
- 不确定时：优先 **workflow 向下调用**，不反向引用编排层。
