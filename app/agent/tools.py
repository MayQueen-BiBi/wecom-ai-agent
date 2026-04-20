from app.services.appointment import (
    get_slots,
    create_appointment
)

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_slots",
            "description": "获取可预约时间",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_appointment",
            "description": "创建预约",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "phone": {"type": "string"},
                    "time": {"type": "string"},
                    "service": {"type": "string"}
                },
                "required": ["name","phone","time","service"]
            }
        }
    }
]


def call_tool(tool_call):
    name = tool_call.function.name
    args = eval(tool_call.function.arguments)

    if name == "get_slots":
        return get_slots()

    if name == "create_appointment":
        return create_appointment(**args)