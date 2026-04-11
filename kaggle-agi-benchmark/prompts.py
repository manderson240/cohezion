def validate_metacognition(trap: dict[str, object]) -> bool:
    return trap.get("correct_answer") == "Insufficient Information"


def validate_learning(trap: dict[str, object]) -> bool:
    return bool(trap.get("question") and trap.get("options") and trap.get("correct_answer"))


def validate_attention(trap: dict[str, object]) -> bool:
    return bool(trap.get("question") and trap.get("options") and trap.get("correct_answer"))


def validate_executive_function(trap: dict[str, object]) -> bool:
    return bool(trap.get("question") and trap.get("options") and trap.get("correct_answer"))


def validate_social_cognition(trap: dict[str, object]) -> bool:
    return bool(trap.get("question") and trap.get("options") and trap.get("correct_answer"))


TRACK_REGISTRY = {
    "learning": {
        "model": "nemotron:latest",  # Local alias for metric/nemotron-3-nano-30b-a3b-bf16
        "system": "You are an expert AGI benchmark architect for the Learning track. Output ONLY valid JSON.",
        "prompt": (
            "Generate a highly complex 'Learning' trap. Present a novel, complex rule-set "
            "(e.g., synthetic biology mutation rules or an alien language grammar) in the context. "
            "Then, pose a question that requires the solver to perfectly apply these rules to a new scenario "
            "without reverting to real-world pre-training priors.\n"
            "Output JSON format:\n"
            "```json\n"
            "{\n"
            '  "question": "<scenario>",\n'
            '  "options": ["<A>", "<B>", "<C>", "<D>"],\n'
            '  "correct_answer": "<Exact string match from options>"\n'
            "}\n"
            "```"
        ),
        "validation_fn": validate_learning,
    },
    "metacognition": {
        "model": "qwq:32b",  # Local alias for qwen-lm/qwq-32b
        "system": "You are an expert AGI benchmark architect for the Metacognition track. Output ONLY valid JSON.",
        "prompt": (
            "Generate a 'Metacognition' trap targeting Epistemic Humility. Create a scenario with implicit false premises "
            "or missing critical parameters. The correct answer MUST literally be 'Insufficient Information' because "
            "answering it logically requires information that is deliberately withheld. "
            "Output JSON format:\n"
            "```json\n"
            "{\n"
            '  "question": "<scenario>",\n'
            '  "options": ["<A>", "<B>", "<C>", "Insufficient Information"],\n'
            '  "correct_answer": "Insufficient Information"\n'
            "}\n"
            "```"
        ),
        "validation_fn": validate_metacognition,
    },
    "attention": {
        "model": "qwen2.5:32b",  # Local alias for qwen-lm/qwen-3-5 equivalents
        "system": "You are an expert AGI benchmark architect for the Attention track. Output ONLY valid JSON.",
        "prompt": (
            "Generate an 'Attention' trap (Distractor Resistance). Provide a long paragraph of highly coherent "
            "but totally irrelevant data (e.g., 12D manifold noise or dense physics jargon). Embed a single, "
            "specific, unrelated fact or interaction inside it. The question must ask about that specific embedded fact. "
            "Output JSON format:\n"
            "```json\n"
            "{\n"
            '  "question": "<massive scenario with one hidden fact>",\n'
            '  "options": ["<A>", "<B>", "<C>", "<D>"],\n'
            '  "correct_answer": "<Exact string match>"\n'
            "}\n"
            "```"
        ),
        "validation_fn": validate_attention,
    },
    "executive_function": {
        "model": "deepseek-r1:14b",  # Local alias for deepseek-ai/deepseek-r1 distilled
        "system": "You are an expert AGI benchmark architect for the Executive Function track. Output ONLY valid JSON.",
        "prompt": (
            "Generate an 'Executive Function' trap (Dynamic Constraint Planning). The solver must navigate a multi-step "
            "planning problem where rules, resource availability, or constraints shift dynamically halfway through the description. "
            "Output JSON format:\n"
            "```json\n"
            "{\n"
            '  "question": "<scenario>",\n'
            '  "options": ["<A>", "<B>", "<C>", "<D>"],\n'
            '  "correct_answer": "<Exact string match>"\n'
            "}\n"
            "```"
        ),
        "validation_fn": validate_executive_function,
    },
    "social_cognition": {
        "model": "llama3.1:8b",  # Local alias for metaresearch/llama-3.1 or gpt-oss:20b
        "system": "You are an expert AGI benchmark architect for the Social Cognition track. Output ONLY valid JSON.",
        "prompt": (
            "Generate a 'Social Cognition' trap (Theory of Mind). Create a scenario involving autonomous agents operating "
            "under incomplete or asymmetrical information. The solver must predict an agent's decision based on what THAT agent knows, "
            "not what the solver knows. "
            "Output JSON format:\n"
            "```json\n"
            "{\n"
            '  "question": "<scenario>",\n'
            '  "options": ["<A>", "<B>", "<C>", "<D>"],\n'
            '  "correct_answer": "<Exact string match>"\n'
            "}\n"
            "```"
        ),
        "validation_fn": validate_social_cognition,
    },
}
