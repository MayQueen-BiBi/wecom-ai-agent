import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class FlowTracker:
    """记录单次对话处理步骤，便于排查与性能观察。"""

    def __init__(self, user_id: str, user_msg: str):
        self.user_id = user_id
        self.user_msg = user_msg
        self.start_time = time.time()
        self.flow_steps: List[Dict[str, Any]] = []
        self.final_answer: Optional[str] = None
        self.error: Optional[str] = None

    def add_step(
        self,
        step_name: str,
        details: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None,
    ) -> None:
        step: Dict[str, Any] = {
            "step_name": step_name,
            "timestamp": time.time(),
            "details": details or {},
        }
        if duration_ms is not None:
            step["duration_ms"] = duration_ms
        self.flow_steps.append(step)

    def set_final_answer(self, answer: str) -> None:
        self.final_answer = answer

    def set_error(self, error: str) -> None:
        self.error = error

    def log_summary(self) -> None:
        total_duration = (time.time() - self.start_time) * 1000

        logger.info("=" * 80)
        logger.info("📋 请求追踪开始 | 用户ID: %s", self.user_id)
        logger.info("🔍 原始查询: %s", self.user_msg)
        logger.info("-" * 80)

        for i, step in enumerate(self.flow_steps, 1):
            duration = step.get("duration_ms", "N/A")
            logger.info("\n[%2d] %s", i, step["step_name"])
            if isinstance(duration, float):
                logger.info("   ⏱️ 耗时: %.2fms", duration)

            if step["details"]:
                for key, value in step["details"].items():
                    if isinstance(value, str) and len(value) > 100:
                        value = value[:100] + "..."
                    logger.info("   %s: %s", key, value)

        logger.info("\n" + "-" * 80)
        if self.error:
            logger.error("❌ 错误: %s", self.error)
        else:
            answer_preview = (
                self.final_answer[:100] + "..."
                if self.final_answer and len(self.final_answer) > 100
                else self.final_answer
            )
            logger.info("✅ 最终回答: %s", answer_preview)
        logger.info("⏱️ 总耗时: %.2fms", total_duration)
        logger.info("=" * 80)
