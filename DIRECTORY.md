# 仓库目录结构说明（重构规划用）

本文描述当前 **Python 应用与测试** 的布局、职责边界与主要依赖方向，便于你做拆分/迁移/命名统一。

---

## 顶层

| 路径 | 说明 |
|------|------|
| `app/` | FastAPI 应用与 Agent 核心代码 |
| `tests/` | `pytest` 单测 |
| `requirements.txt` | 运行时与测试依赖 |

---

## `app/` 总览

```
app/
├── main.py                 # FastAPI 入口、健康检查、dev 调试路由
├── MIGRATION.md            # 历史迁移笔记（可能与当前树不完全同步，以代码为准）
├── config/                 # 环境变量与全局配置
├── wecom/                  # 企微回调：加解密、HTTP 路由
├── services/               # 业务服务（预约、DB 等），偏基础设施
├── state/                  # 会话 / 单次回合运行态（AgentRunState、SessionStore）
├── observability/          # 日志、trace、指标、FlowTracker
├── understanding/          # 统一语义理解（唯一 NL→结构化入口）、Prompt、槽位抽取
├── routing/                # Policy Engine V1：YAML 规则 → route/action
├── critic_rules/           # 生成后清单式校验（Python，非 YAML）
├── agent/                  # 旧「agent 大杂烩」：状态机、编排、RAG、工具等
│   └── dental_v3/          # PRD V3 分层工作流（编排 + 执行子层）
```

**建议依赖方向（目标架构）**

```text
main.py / wecom
    → agent（入口 orchestrator / core）
        → dental_v3.workflow（编排）
            → understanding（仅语义）
            → state（读写）
            → routing（仅策略）
            → execution_layer（检索、LLM、工具；消费 state.action）
            → critic_rules（仅草稿校验）
        → observability（横切）
services / config → 被各层按需引用
```

---

## `app/config/`

| 文件 | 职责 |
|------|------|
| `settings.py` | `QWEN_API_KEY` 等环境变量 |

---

## `app/wecom/`

| 文件 | 职责 |
|------|------|
| `handler.py` | 企微消息路由，经 `app.api.entry.handle_request` → workflow |
| `crypto.py` | 加解密相关 |

---

## `app/services/`

| 文件 | 职责 |
|------|------|
| `appointment.py` | 预约等业务 API |
| `database.py` | SQLAlchemy 等持久化 |

与 Agent 逻辑解耦，可被 `agent/tools` 或将来独立服务调用。

---

## `app/state/`

| 文件 | 职责 |
|------|------|
| `agent_run_state.py` | 单次用户回合可变状态（intent、entities、retrieval、route/action 等） |
| `session_store.py` | 用户级会话存储（内存 / Redis）、澄清计数等 |
| `types.py` | 与状态相关的类型别名等 |
| `__init__.py` | 对外聚合导出 |

**原则**：编排层只通过本包读写「结构化 state」，不在此做 NL 理解。

---

## `app/observability/`

| 文件 | 职责 |
|------|------|
| `logging_config.py` | 日志初始化（`main.py` 使用） |
| `trace.py` | 请求级 trace 结构 |
| `flow_tracker.py` | 步骤级耗时与摘要（workflow 使用） |
| `metrics.py` | 指标更新 |
| `__init__.py` | 聚合导出 |

---

## `app/understanding/`

| 文件 | 职责 |
|------|------|
| `schemas.py` | `UnderstandingResult` 等 schema-first 模型 |
| `llm_node.py` | 统一语义 LLM 调用（无路由/无执行） |
| `unified_understanding.py` | `understand()`、`apply_understanding_result_to_state()` |
| `intent_bridge.py` | V3 intent → legacy intent 字符串（供 workflow 衔接状态机） |
| `intent_classifier.py` | 旧版 12 类意图分类器（测试与兼容场景） |
| `extraction.py` | 槽位/关键词/后处理等 |
| `prompt_templates.py` | 按 `AgentState` 的 Prompt 模板 |
| `__init__.py` | 对外导出 `understand`、`UnderstandingResult` 等 |

---

## `app/routing/`

| 路径 | 职责 |
|------|------|
| `policy_models.py` | `PolicyRow`、`PolicyCondition`、`PolicyRoute`、`PolicyEngine` 输入输出模型 |
| `policy_engine.py` | 加载 YAML、按序匹配、返回 action |
| `routing_policy.py` | `apply_routing_policy(state)`、`evaluate_routing_action(state)`、`set_cache_route` 等 |
| `policies/*.yaml` | V1 仅 risk / retrieval / clarify 三类规则 |
| `__init__.py` | 对外 API |

---

## `app/critic_rules/`

| 路径 | 职责 |
|------|------|
| `context.py` | `CriticContext`（从 `AgentRunState` 抽字段，不解析 user query） |
| `constants.py` | 阈值与正则 |
| `checklist.py` | 编排多条 check |
| `checks/` | 单条规则：`disclaimer`、`retrieval_evidence`、`intent_alignment`、`common` |

---

## `app/agent/`（当前「非分层」遗留区）

| 文件 | 职责（概括） |
|------|----------------|
| `core.py` | 对外 `run_agent` 入口之一 |
| `orchestrator.py` | 调度 `dental_v3` 等 |
| `state_machine.py` | 对话状态机、槽位、与 Prompt 状态联动 |
| `intercepts.py` | 静态拦截（退出词等） |
| `llm_client.py` | 通用 LLM HTTP 调用 |
| `rag_enhanced.py` | 检索实现 |
| `semantic_cache.py` | 语义缓存 |
| `tools.py` | 工具调用（如预约） |
| `faq.py` / `risk_guard.py` / `utils.py` | 辅助逻辑 |

**重构关注点**：与 `dental_v3`、`understanding`、`routing` 的边界；长期可把「编排外」模块迁到 `runtime/` 或 `workflows/`。

---

## `app/agent/dental_v3/`

| 文件 | 职责 |
|------|------|
| `workflow.py` | V3 主流程：拦截 → understanding → 缓存 → 槽位 → 检索 → **routing** → execution |
| `execution_layer.py` | 检索合并、检索执行、按 `state.action` 分发、LLM、critic、缓存写入 |
| `retrieval_guard.py` | 澄清文案、降级文案 |
| `retrieval_metrics.py` | 检索得分计算 |
| `__init__.py` | 导出 `run_agent_v3` |
| `ARCHITECTURE.md` | 模块内说明文档 |

---

## `tests/`

| 文件 | 覆盖范围 |
|------|-----------|
| `conftest.py` | pytest 公共 fixture（若有） |
| `test_basic.py` / `test_agent.py` | 状态机、意图分类等 |
| `test_policy_critic.py` | YAML routing + critic checklist |

---

## 与历史文档的差异提示

- `app/MIGRATION.md` 中可能仍提到已删除路径（如旧 `app/policy`、根级 `logging_config` 转发文件）。**以本文件与 `find app -name '*.py'` 为准。**

---

## 重构时可考虑的目录目标（仅建议，未实施）

| 方向 | 说明 |
|------|------|
| `app/workflows/` | 放置 `dental_v3/workflow` 及未来多工作流 |
| `app/runtime/` | 放置 `execution_layer`、检索守卫等与「单次执行」强相关代码 |
| `app/integrations/` | `wecom`、第三方 API 客户端 |
| 收敛 `app/agent/` | 保留最小入口 + `state_machine`，其余按域迁出 |

若你希望下一步把 **本文件自动同步为脚本生成**（例如 `scripts/gen_directory_md.py`），可以单独加一小段 CI 或 pre-commit。
