# workflows

## 职责

**编排（orchestration）**：

- 节点顺序
- 条件跳转
- state 生命周期（与 reducer 配合）

## 禁止

- retrieval 实现细节
- prompt 拼接与模板定义（归 `understanding/` 与 `execution/` 下 prompts）
- tool 协议实现（归 `execution/` 与 `services/`）

## 状态

本目录为 **Phase 1 占位**；当前编排入口为 `app/agent/dental_v3/workflow.py`。预置子包见 `dental/`。
