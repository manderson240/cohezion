

class TokenEfficiencyTrackerStandalone:
    def __init__(self, budget=5.0):
        self._budget_usd = budget
        self._total_spent = 0.0

    def record_call(self, model, input_tokens, output_tokens):
        cost = 0.0
        total = max(0, input_tokens + output_tokens)
        lower_model = model.lower()
        if "pro" in lower_model or "premium" in lower_model:
            cost = (total / 1_000_000) * 10.0
        elif "flash" in lower_model or "economy" in lower_model:
            cost = (total / 1_000_000) * 0.1
        self._total_spent += cost
        return cost

    def get_budget_status(self):
        return {
            "budget_usd": self._budget_usd,
            "total_spent_usd": self._total_spent,
            "is_exhausted": self._total_spent >= self._budget_usd,
            "is_critical": self._total_spent >= (self._budget_usd * 0.9),
        }


def test_budget_logic():
    print("Starting Standalone Budget Logic Audit")
    tracker = TokenEfficiencyTrackerStandalone(budget=0.01)  # 1 cent budget

    # 1. Critical threshold ($0.01 * 0.9 = $0.009)
    # Gemini Pro: 1000 tokens = $0.01
    # 900 tokens = $0.009
    tracker.record_call("gemini-3-pro", 450, 450)
    status = tracker.get_budget_status()
    print(f"Status after 900 tokens: {status}")
    if status["is_critical"] and not status["is_exhausted"]:
        print("✅ SUCCESS: Critical threshold detected.")
    else:
        print("❌ FAILURE: Critical threshold expected.")

    # 2. Exhaustion threshold
    tracker.record_call("gemini-3-pro", 100, 100)  # Total 1100 tokens = $0.011
    status = tracker.get_budget_status()
    print(f"Status after 1100 tokens: {status}")
    if status["is_exhausted"]:
        print("✅ SUCCESS: Exhaustion threshold detected.")
    else:
        print("❌ FAILURE: Exhaustion threshold expected.")


if __name__ == "__main__":
    test_budget_logic()
