import json
import requests
import logging
import hashlib
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

# 新架构导入
from app.agent.intent_classifier import intent_classifier
from app.agent.state_machine import StateMachine, AgentState
from app.agent.prompt_templates import prompt_manager
from app.agent.faq import base_hybrid_retriever
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
    logger.info(f"--- Processing: {user_msg[:30]} ---")
    
    # 获取用户状态机
    sm = _get_user_state_machine(user_id)
    
    # 1. 静态拦截（风险控制、人工转接、退出意图）
    if (resp := _handle_static_intercepts(user_id, user_msg, sm)):
        return resp

    # 2. 意图识别
    intent, confidence = intent_classifier.classify(user_msg)
    
    # 3. 状态演进
    prev_state = sm.get_current_state()
    current_state = sm.process_intent(intent, confidence)
    
    # 4. 语义缓存检查（考虑意图，避免不同意图的查询互相命中）
    cache_query = f"[{intent}] {user_msg}"
    if (cached := semantic_cache.get(cache_query)):
        _update_metrics(intent, prev_state, current_state, cache_hit=True)
        return cached[0]

    # 5. 槽位提取与同步
    extracted_slots = _extract_slots(user_msg)
    sm.sync_slots(extracted_slots)

    # 6. 获取检索策略与引导信息
    retrieval_strategy = sm.get_retrieval_strategy()
    action_guidance = sm.get_action_guidance()

    # 7. 知识检索
    contexts = base_hybrid_retriever.search(
        user_msg, 
        top_k=retrieval_strategy["top_k"], 
        filter_dict=retrieval_strategy["filter"]
    )
    context_text = "\n".join([f"[{i+1}] {doc}" for i, doc in enumerate(contexts)])

    # 8. 响应生成（分层 Prompt）
    prompt = prompt_manager.format_prompt(
        state=current_state,
        query=user_msg,
        context=context_text,
        **sm.get_context().slots
    )
    
    answer = _call_llm(prompt["system"], prompt["user"])

    # 9. 业务转化层特殊处理
    if current_state == AgentState.BUSINESS_CONVERSION:
        slots = sm.get_context().slots
        # 检查是否所有必要槽位已填充
        if slots["name"] and slots["phone"] and slots["service_type"] and slots["time_slot"]:
            # 执行预约
            logger.info(f"Creating appointment: {slots['name']}, {slots['service_type']}, {slots['time_slot']}")
            result = call_tool(
                "create_appointment",
                {
                    "name": slots["name"],
                    "phone": slots["phone"],
                    "time": slots["time_slot"],
                    "service": slots["service_type"],
                },
            )
            sm.reset()
            return result

    # 10. 后处理与缓存
    final_answer = _post_process_answer(answer, contexts)
    semantic_cache.set(cache_query, final_answer, {"intent": intent, "state": current_state.value})
    _update_metrics(intent, prev_state, current_state, cache_hit=False)

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