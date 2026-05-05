from app.services.appointment import (
    get_slots,
    create_appointment
)

class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self.tools = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """注册默认工具"""
        self.register_tool(
            name="get_slots",
            description="获取可预约时间",
            function=get_slots,
            parameters={}
        )
        
        self.register_tool(
            name="create_appointment",
            description="创建预约",
            function=create_appointment,
            parameters={
                "name": {"type": "string", "description": "用户姓名"},
                "phone": {"type": "string", "description": "手机号码"},
                "time": {"type": "string", "description": "预约时间"},
                "service": {"type": "string", "description": "服务类型"}
            },
            required=["name", "phone", "time", "service"]
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
