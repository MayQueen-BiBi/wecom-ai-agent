# services

## 职责

领域服务：预约、数据库访问等，供 `execution` / `tools` 调用。

## 禁止

- 依赖 `workflow`、`dental_v3` 编排层（避免反向依赖）。

## 依赖方向

见 `app/DEPENDENCY_RULES.md`。
