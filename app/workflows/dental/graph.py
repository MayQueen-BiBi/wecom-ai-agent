"""
Dental V3 Graph：Node + Edge（next 为 lambda state -> 下一节点 id）。

说明：routing 之后边固定指向 \"execution\"（由 state.action 在 core_executor 内分发）；
若未来需按 s.route 分支，可在此处扩展映射表。
"""
from __future__ import annotations

from app.workflows.runtime.graph import Graph
from app.workflows.dental.nodes.clarify_sync_node import run as clarify_sync_run
from app.workflows.dental.nodes.critic_node import run as critic_run
from app.workflows.dental.nodes.execution_node import run as execution_run
from app.workflows.dental.nodes.intercept_node import run as intercept_run
from app.workflows.dental.nodes.retrieval_node import run as retrieval_run
from app.workflows.dental.nodes.routing_node import run as routing_run
from app.workflows.dental.nodes.slot_sync_node import run as slot_sync_run
from app.workflows.dental.nodes.understanding_node import run as understanding_run

DENTAL_GRAPH: Graph = {
    "intercept": {
        "node": intercept_run,
        "next": lambda s: "end" if s.early_exit else "clarify_sync",
    },
    "clarify_sync": {
        "node": clarify_sync_run,
        "next": lambda s: "understanding",
    },
    "understanding": {
        "node": understanding_run,
        "next": lambda s: "end" if s.early_exit else "slot_sync",
    },
    "slot_sync": {
        "node": slot_sync_run,
        "next": lambda s: "retrieval",
    },
    "retrieval": {
        "node": retrieval_run,
        "next": lambda s: "routing",
    },
    "routing": {
        "node": routing_run,
        "next": lambda s: "execution",
    },
    "execution": {
        "node": execution_run,
        "next": lambda s: "critic",
    },
    "critic": {
        "node": critic_run,
        "next": lambda s: "end",
    },
}
