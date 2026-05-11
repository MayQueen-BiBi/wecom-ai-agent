# critic_rules

## 职责

对 **生成草稿** 做清单式校验（免责声明、弱检索强答、意图对齐等）。

## 输入 / 输出

- **输入**：从 state 只读抽取的 `CriticContext` + 草稿字符串。
- **输出**：修订文本与 checklist trace（**目标**：仅 `List[CriticIssue]`，见 `ARCHITECTURE_RULES.md`）。

## 禁止

- 修改 `AgentRunState`
- 调用 `session_store` 或理解模块
