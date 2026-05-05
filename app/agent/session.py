from typing import Dict, Optional, Any


class SessionStateMachine:
    """会话状态机"""
    
    # 定义状态
    STATES = {
        "consulting": "咨询中",
        "appointment_collecting": "预约信息收集",
        "handoff_pending": "等待人工转接",
        "appointment_completed": "预约完成"
    }
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.state = "consulting"
        self.appointment = {
            "name": None,
            "phone": None,
            "service": None,
            "time": None,
        }
        self.handoff = False
        self.tags = []
    
    def transition_to(self, new_state: str) -> bool:
        """状态转换"""
        if new_state not in self.STATES:
            return False
        
        # 定义状态转换规则
        valid_transitions = {
            "consulting": ["appointment_collecting", "handoff_pending"],
            "appointment_collecting": ["appointment_completed", "consulting"],
            "handoff_pending": [],  # 一旦进入等待人工转接，不再转换
            "appointment_completed": ["consulting"]
        }
        
        if new_state in valid_transitions.get(self.state, []):
            self.state = new_state
            return True
        return False
    
    def reset_appointment(self) -> None:
        """重置预约信息"""
        self.appointment = {
            "name": None,
            "phone": None,
            "service": None,
            "time": None,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "state": self.state,
            "appointment": self.appointment,
            "handoff": self.handoff,
            "tags": self.tags
        }


# 会话存储
sessions: Dict[str, SessionStateMachine] = {}


def get_session(user_id: str) -> SessionStateMachine:
    """获取或创建会话"""
    if user_id not in sessions:
        sessions[user_id] = SessionStateMachine(user_id)
    return sessions[user_id]


def reset_appointment(session: SessionStateMachine) -> None:
    """重置预约信息"""
    session.reset_appointment()
    session.transition_to("consulting")
