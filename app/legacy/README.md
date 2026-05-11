# legacy

该目录用于存放**历史遗留** Agent 实现与过渡期迁出代码。

## 规则

- **新功能禁止**继续放入 `legacy/`。
- 迁入须带迁移说明与调用方替换计划。
- 优先将活跃逻辑放在 `workflows/`、`execution/`、`understanding/`、`routing/` 等明确边界包内。
