import json
import requests
import logging
import hashlib
import time
from typing import Optional, Dict, Tuple, Any

# 配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class FlowTracker:
    """
    流程追踪器：记录每个请求的完整处理流程
    """
    
    def __init__(self, user_id: str, user_msg: str):
        self.user_id = user_id
        self.user_msg = user_msg
        self.start_time = time.time()
        self.flow_steps = []
        self.final_answer = None
        self.error = None
        
    def add_step(self, step_name: str, details: Dict = None, duration_ms: float = None):
        """添加处理步骤记录"""
        step = {
            "step_name": step_name,
            "timestamp": time.time(),
            "details": details or {}
        }
        if duration_ms is not None:
            step["duration_ms"] = duration_ms
        self.flow_steps.append(step)
        
    def set_final_answer(self, answer: str):
        """设置最终回答"""
        self.final_answer = answer
        
    def set_error(self, error: str):
        """设置错误信息"""
        self.error = error
        
    def log_summary(self):
        """输出完整的流程日志"""
        total_duration = (time.time() - self.start_time) * 1000
        
        logger.info("=" * 80)
        logger.info(f"📋 请求追踪开始 | 用户ID: {self.user_id}")
        logger.info(f"🔍 原始查询: {self.user_msg}")
        logger.info("-" * 80)
        
        for i, step in enumerate(self.flow_steps, 1):
            duration = step.get("duration_ms", "N/A")
            logger.info(f"\n[{i:2d}] {step['step_name']}")
            if isinstance(duration, float):
                logger.info(f"   ⏱️ 耗时: {duration:.2f}ms")
            
            if step["details"]:
                for key, value in step["details"].items():
                    if isinstance(value, str) and len(value) > 100:
                        value = value[:100] + "..."
                    logger.info(f"   {key}: {value}")
        
        logger.info("\n" + "-" * 80)
        if self.error:
            logger.error(f"❌ 错误: {self.error}")
        else:
            answer_preview = self.final_answer[:100] + "..." if self.final_answer and len(self.final_answer) > 100 else self.final_answer
            logger.info(f"✅ 最终回答: {answer_preview}")
        logger.info(f"⏱️ 总耗时: {total_duration:.2f}ms")
        logger.info("=" * 80)

# 新架构导入
from app.agent.intent_classifier import intent_classifier
from app.agent.state_machine import StateMachine, AgentState
from app.agent.prompt_templates import prompt_manager
from app.agent.rag_enhanced import enhanced_retriever  # 使用增强版检索器（含Query Rewrite）
from app.agent.semantic_cache import semantic_cache
from app.agent.risk_guard import needs_handoff, risk_block_reply
from app.agent.tools import call_tool
from app.config.settings import QWEN_API_KEY

QWEN_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"

# 退出意图关键词
EXIT_KEYWORDS = ["算了", "不预约了", "取消", "退出", "结束"]

# 服务类型列表
SERVICE_TYPES = ["种植牙", "正畸", "洗牙", "补牙", "拔牙", "牙痛检查"]

# LLM 越权检测关键词
FORBIDDEN_PHRASES = ["预约成功", "已为您预约", "挂号成功", "预约已完成"]

# 监控统计
metrics = {
    "intent_distribution": {},
    "state_transitions": {},
    "cache_hits": 0,
    "cache_misses": 0,
    "total_queries": 0
}


def _is_exit_intent(user_msg: str) -> bool:
    """检测退出意图"""
    return any(k in user_msg for k in EXIT_KEYWORDS)


def _extract_phone(user_msg: str) -> Optional[str]:
    """提取手机号"""
    digits = "".join(ch for ch in user_msg if ch.isdigit())
    if len(digits) == 11 and digits.startswith("1"):
        return digits
    return None


def _extract_service(user_msg: str) -> Optional[str]:
    """提取服务类型"""
    for service in SERVICE_TYPES:
        if service in user_msg:
            return service
    return None


def _validate_llm_response(response: str, session_state: str) -> str:
    """验证LLM输出，防止越权"""
    if session_state != "appointment_completed":
        for phrase in FORBIDDEN_PHRASES:
            if phrase in response:
                return "我已记录您的需求，正在为您处理..."
    return response


def _call_llm(system_prompt: str, user_prompt: str) -> str:
    """调用LLM生成响应"""
    if not QWEN_API_KEY:
        logger.warning("QWEN_API_KEY not configured, returning fallback response")
        return "暂时无法生成智能回复，请直接预约或咨询。"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {QWEN_API_KEY}"
    }

    payload = {
        "model": "qwen-flash",
        "input": {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        },
        "parameters": {
            "result_format": "message"
        }
    }

    try:
        resp = requests.post(QWEN_URL, headers=headers, json=payload, timeout=5)
        if resp.status_code == 200:
            result = resp.json()
            if "output" in result:
                return result["output"]["choices"][0]["message"]["content"].strip()
        logger.error(f"LLM API returned non-200 status: {resp.status_code}")
    except Exception as e:
        logger.error(f"LLM call error: {e}")

    return "暂时无法生成回复，请稍后重试。"


def _generate_cache_key(intent: str, query: str) -> str:
    """生成语义缓存键（基于意图和查询的hash）"""
    content = f"{intent}:{query[:100]}"
    return hashlib.md5(content.encode('utf-8')).hexdigest()


def _extract_slots(user_msg: str) -> Dict[str, Any]:
    """从用户消息中提取槽位信息"""
    slots = {}
    
    phone = _extract_phone(user_msg)
    if phone:
        slots["phone"] = phone
    
    service = _extract_service(user_msg)
    if service:
        slots["service_type"] = service
    
    # 尝试提取姓名（简短文本，不含特殊字符，排除常见前缀）
    reserved_phrases = ["帮我预约", "预约", "挂号", "我想预约", "安排时间", "我叫", "我是", "我的名字是"]
    is_reserved = any(phrase in user_msg for phrase in reserved_phrases)
    if len(user_msg.strip()) <= 8 and "@" not in user_msg and not phone and not is_reserved:
        slots["name"] = user_msg.strip()
    
    return slots


def _post_process_answer(answer: str, contexts: list) -> str:
    """后处理回答：去除多余空格，确保格式正确"""
    if not answer:
        return "暂时无法回答您的问题。"
    
    answer = answer.strip()
    
    # 如果没有找到相关上下文，添加提示
    if not contexts:
        answer += "\n\n建议您到院咨询专业医生获取更详细的信息。"
    
    return answer


def _handle_static_intercepts(user_id: str, user_msg: str, sm: StateMachine) -> Optional[str]:
    """逻辑封装：处理无需经过 LLM 的静态链路"""
    # 风险拦截
    if risk_block_reply(user_msg):
        return "对话涉及敏感信息，请咨询线下门诊。"
    
    # 转人工
    if needs_handoff(user_msg):
        return "正在为您转接专业医护人员..."
        
    # 退出重置
    if _is_exit_intent(user_msg):
        sm.reset()
        return "好的，期待下次为您服务。"
    
    return None


def _update_metrics(intent: str, prev_state: AgentState, new_state: AgentState, cache_hit: bool):
    """更新监控指标"""
    metrics["intent_distribution"][intent] = metrics["intent_distribution"].get(intent, 0) + 1
    
    transition_key = f"{prev_state.value}->{new_state.value}"
    metrics["state_transitions"][transition_key] = metrics["state_transitions"].get(transition_key, 0) + 1
    
    metrics["total_queries"] += 1
    if cache_hit:
        metrics["cache_hits"] += 1
    else:
        metrics["cache_misses"] += 1


def get_metrics() -> Dict:
    """获取监控指标"""
    hit_rate = metrics["cache_hits"] / max(metrics["total_queries"], 1) * 100
    return {
        **metrics,
        "cache_hit_rate": f"{hit_rate:.2f}%"
    }


# 多用户状态机存储
user_state_machines: Dict[str, StateMachine] = {}


def _get_user_state_machine(user_id: str) -> StateMachine:
    """获取用户专属状态机（多用户支持）"""
    if user_id not in user_state_machines:
        user_state_machines[user_id] = StateMachine()
        logger.info(f"Created new state machine for user: {user_id}")
    
    return user_state_machines[user_id]


def run_agent(user_id: str, user_msg: str):
    """
    重构后的主入口：中控调度架构
    流程：拦截 -> 意图与状态 -> 槽位同步 -> 检索策略 -> 响应生成
    """
    # 初始化流程追踪器
    tracker = FlowTracker(user_id, user_msg)
    
    try:
        step_start = time.time()
        
        # 1. 获取用户状态机
        sm = _get_user_state_machine(user_id)
        tracker.add_step("获取用户状态机", {
            "用户ID": user_id,
            "状态机已存在": user_id in user_state_machines
        }, (time.time() - step_start) * 1000)

        # 2. 静态拦截（风险控制、人工转接、退出意图）
        step_start = time.time()
        if (resp := _handle_static_intercepts(user_id, user_msg, sm)):
            tracker.add_step("静态拦截命中", {"拦截类型": "风险/转人工/退出", "响应": resp}, (time.time() - step_start) * 1000)
            tracker.set_final_answer(resp)
            tracker.log_summary()
            return resp
        tracker.add_step("静态拦截检查", {"结果": "通过，无拦截"}, (time.time() - step_start) * 1000)

        # 3. 意图识别
        step_start = time.time()
        intent, confidence = intent_classifier.classify(user_msg)
        tracker.add_step("意图识别", {
            "意图": intent,
            "置信度": f"{confidence:.4f}"
        }, (time.time() - step_start) * 1000)

        # 4. 状态演进
        step_start = time.time()
        prev_state = sm.get_current_state()
        current_state = sm.process_intent(intent, confidence)
        tracker.add_step("状态演进", {
            "前一状态": prev_state.value,
            "当前状态": current_state.value,
            "状态栈深度": len(sm.get_context().state_stack)
        }, (time.time() - step_start) * 1000)

        # 5. 语义缓存检查
        step_start = time.time()
        cache_query = f"[{intent}] {user_msg}"
        cached = semantic_cache.get(cache_query)
        if cached:
            tracker.add_step("语义缓存命中", {"缓存键": cache_query[:50]}, (time.time() - step_start) * 1000)
            _update_metrics(intent, prev_state, current_state, cache_hit=True)
            tracker.set_final_answer(cached[0])
            tracker.log_summary()
            return cached[0]
        tracker.add_step("语义缓存检查", {"结果": "未命中", "缓存键": cache_query[:50]}, (time.time() - step_start) * 1000)

        # 6. 槽位提取与同步
        step_start = time.time()
        extracted_slots = _extract_slots(user_msg)
        sm.sync_slots(extracted_slots)
        tracker.add_step("槽位提取", {"提取的槽位": extracted_slots}, (time.time() - step_start) * 1000)

        # 7. 获取检索策略与引导信息
        step_start = time.time()
        retrieval_strategy = sm.get_retrieval_strategy()
        action_guidance = sm.get_action_guidance()
        tracker.add_step("检索策略生成", {
            "过滤条件": retrieval_strategy.get("filter"),
            "Top-K": retrieval_strategy.get("top_k"),
            "搜索类型": retrieval_strategy.get("search_type"),
            "人物角色": action_guidance.get("persona_focus")
        }, (time.time() - step_start) * 1000)

        # 8. 获取对话历史
        step_start = time.time()
        conversation_history = sm.get_context().get_conversation_history()
        history_len = len(sm.get_context().conversation_history)
        tracker.add_step("对话历史获取", {"历史轮数": history_len}, (time.time() - step_start) * 1000)

        # 9. 上下文感知查询增强
        step_start = time.time()
        enhanced_query = user_msg
        last_user_msg = sm.get_context().get_last_user_message()
        if last_user_msg:
            service_keywords = ["种植牙", "正畸", "洗牙", "补牙", "拔牙", "根管治疗"]
            has_service_context = any(keyword in last_user_msg for keyword in service_keywords)
            if has_service_context and len(user_msg) <= 5:
                enhanced_query = f"{last_user_msg} {user_msg}"
                tracker.add_step("上下文感知增强", {
                    "原始查询": user_msg,
                    "增强后查询": enhanced_query,
                    "触发原因": "检测到简短问句+服务上下文"
                }, (time.time() - step_start) * 1000)
            else:
                tracker.add_step("上下文感知增强", {"结果": "无需增强"}, (time.time() - step_start) * 1000)
        else:
            tracker.add_step("上下文感知增强", {"结果": "无历史对话"}, (time.time() - step_start) * 1000)

        # 10. 知识检索（Query Rewrite + Hybrid + Rerank）
        step_start = time.time()
        contexts = enhanced_retriever.search(
            enhanced_query, 
            top_k=retrieval_strategy["top_k"]
        )
        context_text = "\n".join([f"[{i+1}] {doc}" for i, doc in enumerate(contexts)])
        tracker.add_step("知识检索", {
            "检索查询": enhanced_query,
            "召回文档数": len(contexts),
            "上下文摘要": context_text[:150] + "..." if len(context_text) > 150 else context_text
        }, (time.time() - step_start) * 1000)

        # 11. Prompt生成
        step_start = time.time()
        prompt = prompt_manager.format_prompt(
            state=current_state,
            query=user_msg,
            context=context_text,
            history=conversation_history,
            **sm.get_context().slots
        )
        tracker.add_step("Prompt生成", {
            "模板名称": prompt["name"],
            "System Prompt长度": len(prompt["system"]),
            "User Prompt长度": len(prompt["user"])
        }, (time.time() - step_start) * 1000)

        # 12. LLM响应生成
        step_start = time.time()
        answer = _call_llm(prompt["system"], prompt["user"])
        tracker.add_step("LLM响应生成", {
            "回答长度": len(answer),
            "API Key配置": "已配置" if QWEN_API_KEY else "未配置"
        }, (time.time() - step_start) * 1000)

        # 13. 业务转化层特殊处理
        step_start = time.time()
        if current_state == AgentState.BUSINESS_CONVERSION:
            slots = sm.get_context().slots
            if slots["name"] and slots["phone"] and slots["service_type"] and slots["time_slot"]:
                result = call_tool(
                    "create_appointment",
                    {
                        "name": slots["name"],
                        "phone": slots["phone"],
                        "time": slots["time_slot"],
                        "service": slots["service_type"],
                    },
                )
                sm.get_context().add_conversation_turn(user_msg, result)
                sm.reset()
                tracker.add_step("预约执行", {"状态": "成功", "服务类型": slots["service_type"]}, (time.time() - step_start) * 1000)
                tracker.set_final_answer(result)
                tracker.log_summary()
                return result
            else:
                tracker.add_step("预约处理", {"状态": "收集信息中", "缺失槽位": [k for k, v in slots.items() if v is None]}, (time.time() - step_start) * 1000)
        else:
            tracker.add_step("业务转化检查", {"结果": "非转化状态，跳过"}, (time.time() - step_start) * 1000)

        # 14. 后处理与缓存
        step_start = time.time()
        final_answer = _post_process_answer(answer, contexts)
        sm.get_context().add_conversation_turn(user_msg, final_answer)
        semantic_cache.set(cache_query, final_answer, {"intent": intent, "state": current_state.value})
        _update_metrics(intent, prev_state, current_state, cache_hit=False)
        tracker.add_step("后处理与缓存", {
            "回答长度": len(final_answer),
            "是否存入缓存": True
        }, (time.time() - step_start) * 1000)

        tracker.set_final_answer(final_answer)
        
    except Exception as e:
        logger.error(f"Agent execution error: {e}", exc_info=True)
        tracker.set_error(str(e))
        tracker.log_summary()
        return "抱歉，处理您的请求时出现错误，请稍后重试。"
    
    tracker.log_summary()
    return final_answer


# 测试函数
def test_intent_driven_agent():
    """测试意图驱动架构"""
    logger.info("=== Starting intent-driven agent test ===")
    
    test_cases = [
        ("我牙疼", "症状诊断"),
        ("什么是种植牙", "方案科普"),
        ("种植牙多少钱", "价格询盘"),
        ("帮我预约", "预约引导"),
        ("医院在哪里", "就诊保障"),
    ]
    
    test_user_id = "test_user_001"
    
    for query, expected in test_cases:
        logger.info(f"\n=== Test case: {expected} ===")
        logger.info(f"User query: {query}")
        
        answer = run_agent(test_user_id, query)
        logger.info(f"Response: {answer}")
    
    metrics_result = get_metrics()
    logger.info("\n=== Test metrics ===")
    logger.info(f"Total queries: {metrics_result['total_queries']}")
    logger.info(f"Cache hit rate: {metrics_result['cache_hit_rate']}")
    logger.info(f"Intent distribution: {metrics_result['intent_distribution']}")


if __name__ == "__main__":
    test_intent_driven_agent()