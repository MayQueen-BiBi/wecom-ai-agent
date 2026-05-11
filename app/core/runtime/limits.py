"""
运行时资源上限（超时 / 并发）。可按环境变量或部署配置调大。

说明：Phase 7.6 规格中的 3s 全链路对含 LLM 的图过紧，默认采用更稳妥的全图预算；
压测或金丝雀环境可下调 ``MAX_WORKFLOW_TIME_S``。
"""
from __future__ import annotations

# 预留：流式 / token 级超时（秒）
MAX_TOKENS_TIMEOUT_S = 8.0

# 单次 Graph + LLM 等整回合上限（秒）
MAX_WORKFLOW_TIME_S = 45.0

# 全库并发中的 in-flight 请求上限（由 entry 层信号量执行）
MAX_CONCURRENT_REQUESTS = 50
