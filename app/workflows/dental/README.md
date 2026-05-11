# dental workflow（预结构）

未来本工作流将 **node 化**，阶段顺序示例：

```text
intercept → understanding → routing → retrieval → generation → critic
```

## 当前阶段

- **仅目录与说明**：编排逻辑仍在 `app/agent/dental_v3/workflow.py`。
- 不迁移业务代码、不引入 graph 框架。

## 节点占位

见 `nodes/`：`intercept_node`、`understanding_node`、`routing_node`、`execution_node`、`critic_node`（占位 `async def run`）。
