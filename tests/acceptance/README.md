# Phase 7 Final — Production Acceptance（验收说明）

## 分层

| 层级 | 文件 | 关注点 |
|------|------|--------|
| L1 | `test_l1_functional.py` | 单请求功能正确性 |
| L2 | `test_l2_routing.py` | 路由稳定性（命中率阈值） |
| L3 | `test_l3_stress.py` | 连续请求无崩溃；轻量 tracemalloc |
| L4 | `test_l4_resilience.py` | 空输入 / 非法 user_id / 超时降级 |
| L5 | `test_l5_trace.py` | trace 阶段与 graph_step diff 元数据 |

## 环境变量

| 变量 | 默认 | 说明 |
|------|------|------|
| `ACCEPTANCE_STRESS_ITERATIONS` | `100` | L3 循环次数 |
| `ACCEPTANCE_L2_TRIALS` | `8` | L2 每场景重复次数 |
| `ACCEPTANCE_L2_MIN_HIT_RATE` | `0.9` | L2 命中率下限 |

## 上线门槛（与代码断言对应关系）

| 指标 | 门槛 | 实现方式 |
|------|------|----------|
| Functional accuracy ≥ 95% | 目标 | L1 用例全绿为基线；扩展用例可提高覆盖 |
| Routing accuracy ≥ 90% | **已断言** | L2 `MIN_HIT_RATE` 默认 0.9 |
| Crash rate = 0% | **已断言** | L3/L4 + 全 suite 无异常退出 |
| Timeout rate < 1% | 目标 | L4 超时单测验证降级路径 |
| Fallback coverage = 100% | **已部分断言** | L4 空输入/超时必有文案 |
| Trace coverage = 100% | **已断言** | L5 关键阶段 + `changed_keys` |

## 判定

- **PASS**：`pytest tests/acceptance/` 全绿，且生产依赖（企微 env、LLM key）在目标环境已配置。
- **WARN**：L2 在真实流量下需调大 `TRIALS` 或放宽允许集合后仍低于阈值。
- **FAIL**：任一层级失败或 CI 无法稳定复现（应先修 flaky 再谈上线）。

运行：

```bash
pytest tests/acceptance/ -q
```
