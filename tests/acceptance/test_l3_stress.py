"""
L3 压力稳定性：连续请求无崩溃、无挂死。

内存泄漏需线下 profiler；此处仅做轻量 tracemalloc 记录（默认不断言峰值）。
"""
from __future__ import annotations

import gc
import os
import tracemalloc

import pytest

from app.api.entry import invoke_request
from app.api.protocol import AgentRequest

STRESS_ITERATIONS = int(os.environ.get("ACCEPTANCE_STRESS_ITERATIONS", "100"))
TEXT = "牙齿疼怎么办"


@pytest.fixture
def uid() -> str:
    return "acc_l3_stress"


def test_l3_sequential_stress_no_crash(uid: str) -> None:
    tracemalloc.start()
    try:
        for i in range(STRESS_ITERATIONS):
            res = invoke_request(
                AgentRequest(
                    user_id=f"{uid}_{i}",
                    text=TEXT,
                    channel="acceptance_l3",
                    metadata={"i": i},
                )
            )
            assert res.reply is not None
            assert res.trace_id
        gc.collect()
        _current, peak = tracemalloc.get_traced_memory()
        # 仅记录，避免在沙箱/不同 Python 版本上 flaky；线下对比 peak。
        assert peak < 512 * 1024 * 1024, f"peak traced memory suspiciously high: {peak}"
    finally:
        tracemalloc.stop()
