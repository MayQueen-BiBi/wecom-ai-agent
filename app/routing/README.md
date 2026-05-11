# routing

## 职责

**确定性**策略：`state`（risk、retrieval_score、clarify_count 等）→ `action` / `route`。

## 输入 / 输出

- **输入**：`AgentRunState`（结构化字段）。
- **输出**：`PolicyEvaluationResult` 语义；trace 写入由 reducer `apply_routing_result` 归并（目标路径）。

## 禁止

- LLM、检索、生成 Prompt。

## 配置

规则见 `app/routing/policies/*.yaml`。
