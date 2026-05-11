# state

## 职责

- `AgentRunState`：单次用户回合可变状态（迁移期允许既有突变；**冻结后新增写入须经 reducer**）。
- `session_store`：用户级会话与澄清计数等。
- `reducers.py`：**纯函数**状态归并（无副作用、无 IO）。

## 禁止

- 在 `reducers` 中打日志、访问 DB、调用 LLM。

## 相关

- `app/ARCHITECTURE_RULES.md` Rule 5
