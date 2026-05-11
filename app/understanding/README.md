# understanding

## 职责

统一 **NL → 结构化语义**（`UnderstandingResult`）；唯一理解入口。

## 输入 / 输出

- **输入**：用户消息、可选上文。
- **输出**：结构化结果；经 `state.reducers.apply_understanding_result` 合并入 `AgentRunState`（目标路径）。

## 禁止

- retrieval、routing、tool、最终用户回复生成。

## 依赖方向

仅向下依赖 `config` 等基础模块；不依赖 `workflow`（见 `DEPENDENCY_RULES.md`）。
