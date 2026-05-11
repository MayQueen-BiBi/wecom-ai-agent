# 架构硬规则（Architecture Freeze）

## Rule 1 — Understanding

**Understanding 只负责：**

```text
NL → Structured Result
```

**禁止：**

- retrieval
- route / action 决策
- tool call
- 对用户最终 response 的生成（除结构化理解所需内部调用外）

---

## Rule 2 — Routing

**Routing 必须 deterministic。**

**禁止：**

- LLM
- retrieval
- prompt generation（除读取 YAML 等配置外）

**Routing 只能：**

```text
state → action
```

---

## Rule 3 — Critic

**Critic 不允许修改 state。**

**目标返回形态：**

```python
List[CriticIssue]
```

（当前代码路径仍以修订后文本 + trace 为主；新代码须向该形态收敛，不在本阶段强行改行为。）

---

## Rule 4 — Workflow 与 Prompt

**Workflow 不允许直接写 Prompt。**

**Prompt 必须位于：**

- `understanding/`（理解侧模板，如 `prompt_templates.py`）
- `execution/`（执行侧模板；迁移期仍在 `agent`/`dental_v3` 内的模板属 **legacy**，新 Prompt 禁止再加在 `agent/`）

---

## Rule 5 — State 写入

**所有状态修改必须经过 reducer（`app/state/reducers.py`）。**

**禁止：**

```python
state.xxx = yyy
```

散落在业务模块的新增写入（存量代码逐步迁移；**冻结期起禁止新增**此类写法）。

---

## Rule 6 — `agent/` 冻结

`app/agent/` **不再扩张**；新逻辑须落在 `workflows/`、`execution/`、`core/`（预留）或 `legacy/`（仅收容历史代码）。
