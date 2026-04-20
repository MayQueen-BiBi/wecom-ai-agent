FAQ_KB = [
    {
        "keywords": ["种植牙", "种牙", "缺牙"],
        "answer": "种植牙通常分为检查评估、制定方案、植入与复查几个阶段。费用会因牙位、骨量和材料不同而变化，建议到院拍片后给出准确方案。"
    },
    {
        "keywords": ["正畸", "矫正", "牙套"],
        "answer": "正畸需要先进行口腔检查与面诊评估，再确定是否适合隐形或托槽方案。矫正周期和费用与牙齿基础情况有关。"
    },
    {
        "keywords": ["洗牙", "洁牙", "牙结石"],
        "answer": "洁牙主要用于清除牙结石和牙菌斑，通常建议定期进行。是否需要进一步治疗要以医生检查结果为准。"
    },
    {
        "keywords": ["医生", "专家", "资质"],
        "answer": "我们可安排您到院与对应科室医生面诊，医生资质和擅长方向会在接诊前为您详细介绍。"
    },
    {
        "keywords": ["营业时间", "上班时间", "几点开门"],
        "answer": "门诊常规接诊时间以院方排班为准。您可以告诉我您方便的时段，我先帮您登记预约。"
    },
    {
        "keywords": ["价格", "多少钱", "费用", "贵吗"],
        "answer": "不同项目费用会根据检查结果和治疗方案变化。为了保证准确，我们只提供价格区间参考，最终以医生面诊评估为准。"
    },
]


def faq_search(user_text: str) -> str | None:
    text = user_text.lower()
    for item in FAQ_KB:
        if any(keyword in text for keyword in item["keywords"]):
            return item["answer"]
    return None
