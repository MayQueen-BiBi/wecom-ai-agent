# 工具注册表（预约等服务）；由 ``app.core.tools`` 导出。
from app.services.appointment import (
    get_slots,
    create_appointment,
    get_doctors,
    get_doctor_by_id,
    get_appointments,
    update_appointment_status,
    recommend_doctors
)

class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self.tools = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """注册默认工具"""
        # 获取可预约时段
        self.register_tool(
            name="get_slots",
            description="获取可预约时间",
            function=get_slots,
            parameters={}
        )
        
        # 创建预约
        self.register_tool(
            name="create_appointment",
            description="创建预约",
            function=create_appointment,
            parameters={
                "name": {"type": "string", "description": "用户姓名"},
                "phone": {"type": "string", "description": "手机号码"},
                "time": {"type": "string", "description": "预约时间"},
                "service": {"type": "string", "description": "服务类型"},
                "doctor_id": {"type": "string", "description": "医生ID（可选）"}
            },
            required=["name", "phone", "time", "service"]
        )
        
        # 获取医生列表
        self.register_tool(
            name="get_doctors",
            description="获取医生列表",
            function=get_doctors,
            parameters={
                "department": {"type": "string", "description": "科室名称（可选）"}
            }
        )
        
        # 获取医生详情
        self.register_tool(
            name="get_doctor_by_id",
            description="根据ID获取医生信息",
            function=get_doctor_by_id,
            parameters={
                "doctor_id": {"type": "string", "description": "医生ID"}
            },
            required=["doctor_id"]
        )
        
        # 获取预约列表
        self.register_tool(
            name="get_appointments",
            description="获取所有预约",
            function=get_appointments,
            parameters={
                "status": {"type": "string", "description": "预约状态过滤（可选）"}
            }
        )
        
        # 更新预约状态
        self.register_tool(
            name="update_appointment_status",
            description="更新预约状态",
            function=update_appointment_status,
            parameters={
                "appointment_id": {"type": "string", "description": "预约ID"},
                "status": {"type": "string", "description": "新状态（pending/confirmed/visited/canceled）"},
                "visit_notes": {"type": "string", "description": "就诊记录（可选）"}
            },
            required=["appointment_id", "status"]
        )
        
        # 推荐医生
        self.register_tool(
            name="recommend_doctors",
            description="根据服务类型推荐医生",
            function=recommend_doctors,
            parameters={
                "service_type": {"type": "string", "description": "服务类型（如种植牙、正畸、洗牙等）"}
            },
            required=["service_type"]
        )
    
    def register_tool(self, name: str, description: str, function, parameters: dict, required: list = None):
        """注册工具"""
        tool_def = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": parameters
                }
            }
        }
        
        if required:
            tool_def["function"]["parameters"]["required"] = required
        
        self.tools[name] = {
            "definition": tool_def,
            "function": function
        }
    
    def get_tool_definitions(self):
        """获取所有工具定义"""
        return [tool["definition"] for tool in self.tools.values()]
    
    def call_tool(self, name: str, args: dict):
        """调用工具"""
        if name not in self.tools:
            return {"error": f"unknown tool: {name}"}
        
        try:
            tool = self.tools[name]
            result = tool["function"](**args)
            return result
        except Exception as e:
            return {"error": str(e)}

# 初始化工具注册表
tool_registry = ToolRegistry()

# 导出工具定义
tools = tool_registry.get_tool_definitions()

# 导出调用工具函数
def call_tool(name: str, args: dict):
    return tool_registry.call_tool(name, args)
