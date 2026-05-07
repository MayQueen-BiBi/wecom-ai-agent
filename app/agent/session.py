from typing import Dict, Optional, Any
from app.agent.state_machine import StateMachine

# 会话存储（简化版）
class Session:
    """会话对象，存储用户相关信息"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.created_at = None
        self.last_active = None
        self.tags = []
        # 状态机现在在 core.py 中管理

# 会话存储
sessions: Dict[str, Session] = {}


def get_session(user_id: str) -> Session:
    """获取或创建会话"""
    if user_id not in sessions:
        sessions[user_id] = Session(user_id)
    return sessions[user_id]


def reset_appointment(session: Session) -> None:
    """重置预约信息（保持兼容旧接口）"""
    # 在新架构中，预约信息存储在状态机的槽位中
    pass


def get_session_count() -> int:
    """获取当前活跃会话数"""
    return len(sessions)


def cleanup_inactive_sessions(max_inactive_seconds: int = 3600) -> int:
    """清理长时间不活跃的会话"""
    import time
    now = time.time()
    cleaned = 0
    to_remove = []
    
    for user_id, session in sessions.items():
        if session.last_active and now - session.last_active > max_inactive_seconds:
            to_remove.append(user_id)
            cleaned += 1
    
    for user_id in to_remove:
        del sessions[user_id]
    
    return cleaned