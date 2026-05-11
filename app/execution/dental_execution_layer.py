"""
Execution Layer：薄封装 — 调 core_executor + reducer + session/cache/metrics 副作用。
检索纯函数仍在此模块暴露给 adapter。
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Tuple

from app.observability.metrics import update_metrics
from app.core.cache.cache import semantic_cache
from app.core.runtime.state_machine import AgentState
from app.execution.core_executor import execute_sync
from app.execution.rag_enhanced import enhanced_retriever
from app.execution.retrieval_metrics import compute_retrieval_score
from app.execution.schemas import ExecutionResult
from app.state.reducers import apply_execution_result, clear_session_updates

if TYPE_CHECKING:
    from app.core.runtime.state_machine import StateMachine
    from app.state.agent_run_state import AgentRunState

def compute_merged_retrieval_query(state: "AgentRunState", sm: "StateMachine") -> str:
    """省略表达：规则拼接上一轮用户话 + 当前句（非意图识别）；不修改 state。"""
    rq = state.rewritten_query
    last_u = sm.get_context().get_last_user_message()
    if last_u and len(state.user_msg.strip()) <= 6:
        rq = f"{last_u} {state.user_msg}".strip()
    return rq


def run_execution_retrieval(
    merged_retrieval_query: str,
    sm: "StateMachine",
) -> Tuple[List[str], float, Dict[str, Any]]:
    """检索子过程：不修改 state，返回 contexts / score / trace。"""
    strategy = sm.get_retrieval_strategy()
    top_k = int(strategy.get("top_k", 3))
    contexts = enhanced_retriever.search_direct(
        merged_retrieval_query,
        top_k=top_k,
    )
    retrieval_score = compute_retrieval_score(contexts)
    trace: Dict[str, Any] = {
        "query": merged_retrieval_query,
        "top_k": top_k,
        "num_docs": len(contexts),
        "retrieval_score": retrieval_score,
    }
    return contexts, retrieval_score, trace


def merge_retrieval_query_rules(state: "AgentRunState", sm: "StateMachine") -> None:
    """兼容名：原地写入 merged_retrieval_query（遗留调用方）。"""
    state.merged_retrieval_query = compute_merged_retrieval_query(state, sm)


def execution_retrieval(state: "AgentRunState", sm: "StateMachine") -> None:
    """兼容名：原地写入检索结果（遗留调用方）。"""
    merged = state.merged_retrieval_query or compute_merged_retrieval_query(state, sm)
    ctx, score, trace = run_execution_retrieval(merged, sm)
    state.contexts = ctx
    state.retrieval_score = score
    state.trace["execution_retrieval"] = trace


def complete_generation_dispatch(
    state: "AgentRunState",
    er: ExecutionResult,
    *,
    user_id: str,
    prev_sm_state: AgentState,
    current_sm_state: AgentState,
    legacy_intent_for_metrics: str,
) -> Tuple[str, "AgentRunState"]:
    """core_executor 输出后：reducer + session + cache/metrics（与 execution_dispatch 语义一致）。"""
    state = apply_execution_result(state, er)
    _flush_session_ops(user_id, state.session_updates)
    state = clear_session_updates(state)

    cw = er.meta.get("cache_write")
    if cw:
        semantic_cache.set(cw["key"], cw["value"], cw["metadata"])
    if er.meta.get("metrics") is not None:
        update_metrics(
            legacy_intent_for_metrics,
            prev_sm_state,
            current_sm_state,
            cache_hit=bool(er.meta["metrics"].get("cache_hit", False)),
        )

    return er.response, state


def _flush_session_ops(user_id: str, ops: List[Dict[str, Any]]) -> None:
    from app.state.session_store import session_store

    for op in ops or []:
        uid = str(op.get("user_id", user_id))
        if op.get("op") == "increment_clarify":
            session_store.increment_clarify(uid)
        elif op.get("op") == "reset_clarify":
            session_store.reset_clarify(uid)


def execution_dispatch(
    state: "AgentRunState",
    sm: "StateMachine",
    *,
    cache_query: str,
    prev_sm_state: AgentState,
    current_sm_state: AgentState,
    legacy_intent_for_metrics: str,
) -> Tuple[str, "AgentRunState"]:
    """core_executor → reducer → session；cache/metrics 在 state 合并后处理。"""
    er = execute_sync(
        state,
        state.action,
        sm=sm,
        cache_query=cache_query,
        prev_sm_state=prev_sm_state,
        current_sm_state=current_sm_state,
        legacy_intent_for_metrics=legacy_intent_for_metrics,
    )
    return complete_generation_dispatch(
        state,
        er,
        user_id=state.user_id,
        prev_sm_state=prev_sm_state,
        current_sm_state=current_sm_state,
        legacy_intent_for_metrics=legacy_intent_for_metrics,
    )


def sync_clarify_count_from_session(state: "AgentRunState") -> None:
    """遗留：原地写入 clarify_count。"""
    from app.state.session_store import session_store

    snap = session_store.snapshot(state.user_id)
    state.clarify_count = int(snap.get("clarify_count", 0))
