# 依赖规则 V2（演进存档）

Phase 7 起，**`app/agent` 已删除**；最终约束见 **`app/DEPENDENCY_RULES_FINAL.md`**。

历史要点：

* `app/core`、`app/execution`、`app/workflows`、`app/routing`、`app/state`、`app/understanding` 均不得依赖已移除的 `app.agent`。
* 生产入口已迁至 **`app/api/entry.py`**；原 `app/main.py` / `app/wecom/handler.py` 对 `app.agent` 的白名单机制已废止。

校验命令不变：

```bash
python scripts/check_dependency.py
```
