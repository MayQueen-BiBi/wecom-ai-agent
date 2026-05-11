"""架构守卫：依赖图校验等。"""
from app.guards.dependency_guard import check_dependency_graph

__all__ = ["check_dependency_graph"]
