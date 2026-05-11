# observability

## 职责

日志初始化、请求 trace、FlowTracker 步骤、业务指标。

## 输入 / 输出

- **输入**：各层传入的结构化事件与 state 快照（只读）。
- **输出**：日志行、指标更新。

## 禁止

- 作为唯一路径修改对话业务结论（不替代 `state` / reducer）。
