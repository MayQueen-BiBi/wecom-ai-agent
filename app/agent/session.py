from typing import Dict


sessions: Dict[str, dict] = {}


def get_session(user_id: str) -> dict:
    if user_id not in sessions:
        sessions[user_id] = {
            "state": "consulting",
            "appointment": {
                "name": None,
                "phone": None,
                "service": None,
                "time": None,
            },
            "handoff": False,
            "tags": [],
        }
    return sessions[user_id]


def reset_appointment(session: dict) -> None:
    session["appointment"] = {
        "name": None,
        "phone": None,
        "service": None,
        "time": None,
    }
