from typing import Any, Dict

from app.core.runtime.state_machine import AgentState

metrics: Dict[str, Any] = {
    "intent_distribution": {},
    "state_transitions": {},
    "cache_hits": 0,
    "cache_misses": 0,
    "total_queries": 0,
}


def update_metrics(
    intent: str,
    prev_state: AgentState,
    new_state: AgentState,
    cache_hit: bool,
) -> None:
    metrics["intent_distribution"][intent] = (
        metrics["intent_distribution"].get(intent, 0) + 1
    )

    transition_key = f"{prev_state.value}->{new_state.value}"
    metrics["state_transitions"][transition_key] = (
        metrics["state_transitions"].get(transition_key, 0) + 1
    )

    metrics["total_queries"] += 1
    if cache_hit:
        metrics["cache_hits"] += 1
    else:
        metrics["cache_misses"] += 1


def get_metrics() -> Dict[str, Any]:
    hit_rate = metrics["cache_hits"] / max(metrics["total_queries"], 1) * 100
    return {
        **metrics,
        "cache_hit_rate": f"{hit_rate:.2f}%",
    }
