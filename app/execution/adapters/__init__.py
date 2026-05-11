"""execution 适配层：薄封装现有 dental_v3 执行逻辑。"""
from app.execution.adapters.generation_adapter import execute_generation_dispatch
from app.execution.adapters.retrieval_adapter import execute_retrieval

__all__ = ["execute_retrieval", "execute_generation_dispatch"]
