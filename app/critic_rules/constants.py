"""与 policy 对齐的检索阈值（禁止在证据不足时强答）。"""

RETRIEVAL_SCORE_STRONG_ANSWER_FORBID_MAX: float = 0.25

DISCLAIMER_TERMS: tuple[str, ...] = (
    "面诊",
    "医生",
    "因人而异",
    "不可替代",
    "诊疗",
    "评估",
    "到院",
)

DEFAULT_DISCLAIMER_SUFFIX: str = " 具体情况因人而异，建议您到院由医生面诊评估。"

# 绝对化 / 超检索承诺
ABSOLUTE_PROMISE_PATTERN: str = r"(保证|一定|百分百|包治|永不复发|肯定能好|绝对有效)"

# 低证据时禁止的「强医疗结论」口吻（与绝对承诺叠加使用）
STRONG_OUTCOME_PATTERN: str = r"(治愈|根治|无副作用|零风险|不会复发)"
