"""V3 意图 → 现有 StateMachine legacy 意图（供 workflow 在 Understanding 之后应用，非 Understanding 内决策）。"""


def v3_to_legacy_intent(v3_intent: str) -> str:
    mapping = {
        "medical_consulting": "Procedure_Explain",
        "price_question": "Price_Inquiry",
        "pain_question": "Fear_Relief",
        "recovery_question": "Process_Flow",
        "appointment": "Lead_Generation",
        "insurance": "Price_Inquiry",
        "comparative": "Comparative_Analysis",
        "logistics": "Logistics_Support",
        "out_of_scope": "Out_of_Scope",
    }
    return mapping.get(v3_intent, "Procedure_Explain")
