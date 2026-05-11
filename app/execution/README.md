# execution

## 职责

**真正执行动作**，包括但不限于：

- retrieval（检索、重排占位）
- generation（LLM 调用、回复草稿）
- tool call（预约等）
- rerank（若引入）
- responder（后处理、写缓存等执行侧步骤）

## 禁止

- route decision（归 `app/routing`）
- NL understanding（归 `app/understanding`）

## 状态

本目录为 **Phase 1 占位**；当前生产路径仍在 `app/agent/dental_v3/execution_layer.py`，迁移按迭代逐步替换 import，不改变业务行为。
