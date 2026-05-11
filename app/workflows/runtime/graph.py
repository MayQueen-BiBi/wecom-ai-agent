"""轻量 Graph Runtime（无外部框架）。"""
from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, Optional, TypedDict


class NodeSpec(TypedDict):
    node: Callable[[Any], Awaitable[Any]]
    next: Callable[[Any], str]


Graph = Dict[str, NodeSpec]


async def run_node(node_fn: Callable[[Any], Awaitable[Any]], state: Any) -> Any:
    return await node_fn(state)


async def run_graph(
    graph: Graph,
    start_node: str,
    state: Any,
    *,
    on_after_node: Optional[Callable[[str, Any, Any], None]] = None,
) -> Any:
    """
    按边动态跳转执行节点；节点必须返回完整 state（由 reducer 产生）。
    终止：next 返回 \"end\" 或未知节点名（防护性 break）。

    ``on_after_node(node_id, state_before, state_after)`` 在每个节点成功后调用（可观测 / diff）。
    """
    current = start_node
    max_steps = 64
    steps = 0
    while current != "end" and steps < max_steps:
        steps += 1
        spec = graph.get(current)
        if spec is None:
            break
        prev = state
        state = await run_node(spec["node"], state)
        if on_after_node is not None:
            on_after_node(current, prev, state)
        nxt = spec["next"](state)
        current = nxt
    return state
