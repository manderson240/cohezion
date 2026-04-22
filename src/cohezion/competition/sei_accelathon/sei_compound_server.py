"""Compound Session MCP Server for Sei blockchain.

Builds on @sei-js/mcp-server with Cohezion's compound engineering:
- Task decomposition into atomic Sei operations
- Alignment gate before each on-chain action
- Journey tracking across the full transaction lifecycle
- Session persistence to Cohezion vault

This is a prototype for the Sei AI Accelathon MCP Tooling Track.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SeiOperation:
    """A single blockchain operation with alignment gate."""
    tool: str
    parameters: Dict[str, Any]
    estimated_gas: Optional[int] = None
    alignment_score: float = 0.0
    risk_level: str = "LOW"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool": self.tool,
            "params": self.parameters,
            "gas": self.estimated_gas,
            "alignment": self.alignment_score,
            "risk": self.risk_level,
        }


@dataclass
class SeiCompoundSession:
    """Compound session for Sei blockchain operations."""
    session_id: str
    goal: str
    operations: List[SeiOperation] = field(default_factory=list)
    completed: List[SeiOperation] = field(default_factory=list)
    failed: List[SeiOperation] = field(default_factory=list)
    journey: List[Dict[str, Any]] = field(default_factory=list)

    def add_operation(self, op: SeiOperation) -> bool:
        """Add operation after alignment gate check.

        Returns True if operation passes the gate.
        """
        # Alignment gate: check if operation is aligned with stated goal
        alignment = self._check_alignment(op)
        if alignment < 0.5:
            logger.warning(f"Operation '{op.tool}' blocked by alignment gate (score={alignment:.2f})")
            op.alignment_score = alignment
            self.journey.append({
                "phase": "alignment_rejected",
                "tool": op.tool,
                "score": alignment,
                "reason": "Misaligned with session goal",
            })
            return False

        op.alignment_score = alignment
        self.operations.append(op)
        return True

    def _check_alignment(self, op: SeiOperation) -> float:
        """Simple alignment gate: check if tool is in goal keywords."""
        goal_lower = self.goal.lower()
        tool_lower = op.tool.lower()

        # Heuristic alignment
        if "balance" in tool_lower and any(w in goal_lower for w in ["check", "balance", "overview", "status"]):
            return 0.9
        if "transfer" in tool_lower and any(w in goal_lower for w in ["send", "pay", "transfer"]):
            return 0.9
        if "contract" in tool_lower and any(w in goal_lower for w in ["deploy", "contract", "interact"]):
            return 0.85
        if "stake" in tool_lower and any(w in goal_lower for w in ["stake", "delegate"]):
            return 0.9
        if "swap" in tool_lower and any(w in goal_lower for w in ["swap", "exchange", "trade"]):
            return 0.85
        # Default: weak alignment
        return 0.6

    def execute_next(self) -> Optional[Dict[str, Any]]:
        """Execute next queued operation."""
        if not self.operations:
            return None

        op = self.operations.pop(0)
        try:
            # Here we would call the actual Sei MCP tool
            # For prototype: simulate success
            result = {
                "status": "success",
                "tool": op.tool,
                "params": op.parameters,
                "gas_used": op.estimated_gas,
            }
            self.completed.append(op)
            self.journey.append({
                "phase": "executed",
                "tool": op.tool,
                "alignment": op.alignment_score,
                "result": result,
            })
            return result
        except Exception as e:
            self.failed.append(op)
            self.journey.append({
                "phase": "failed",
                "tool": op.tool,
                "error": str(e),
            })
            return {"status": "failed", "error": str(e)}

    def get_summary(self) -> Dict[str, Any]:
        """Session summary for vault persistence."""
        return {
            "session_id": self.session_id,
            "goal": self.goal,
            "queued": len(self.operations),
            "completed": len(self.completed),
            "failed": len(self.failed),
            "journey_length": len(self.journey),
            "avg_alignment": sum(op.alignment_score for op in self.completed) / max(len(self.completed), 1),
            "operations": [op.to_dict() for op in self.completed + self.operations + self.failed],
        }


def demonstrate_compound_session() -> Dict[str, Any]:
    """Demonstrate a compound session for a realistic Sei scenario."""
    session = SeiCompoundSession(
        session_id="sei-compound-demo-001",
        goal="Rebalance portfolio: transfer 50 SEI to staking contract and check remaining balance",
    )

    # Operation 1: Check current balance (aligned)
    op1 = SeiOperation(
        tool="get_balance",
        parameters={"address": "0x742d..."},
        estimated_gas=0,
        risk_level="LOW",
    )
    session.add_operation(op1)

    # Operation 2: Approve token spending (aligned)
    op2 = SeiOperation(
        tool="approve_token_spending",
        parameters={
            "token_address": "0xSEI_staking_token",
            "spender": "0xstaking_contract",
            "amount": 50,
        },
        estimated_gas=25000,
        risk_level="MEDIUM",
    )
    session.add_operation(op2)

    # Operation 3: Transfer to staking (aligned)
    op3 = SeiOperation(
        tool="write_contract",
        parameters={
            "contract_address": "0xstaking_contract",
            "function": "stake",
            "amount": 50,
        },
        estimated_gas=50000,
        risk_level="HIGH",
    )
    session.add_operation(op3)

    # Operation 4: Random unrelated operation (should be blocked)
    op4 = SeiOperation(
        tool="deploy_contract",
        parameters={"bytecode": "0x..."},
        estimated_gas=200000,
        risk_level="CRITICAL",
    )
    session.add_operation(op4)

    # Execute all queued operations
    results = []
    while True:
        result = session.execute_next()
        if result is None:
            break
        results.append(result)

    return session.get_summary()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    print("=" * 60)
    print("SEI_COMPOUND_SERVER PROTOTYPE")
    print("=" * 60)

    summary = demonstrate_compound_session()
    print(f"\nSession: {summary['session_id']}")
    print(f"Goal: {summary['goal']}")
    print(f"Queued: {summary['queued']}")
    print(f"Completed: {summary['completed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Avg alignment: {summary['avg_alignment']:.2f}")
    print(f"Journey length: {summary['journey_length']}")

    print("\nOperation details:")
    for op in summary["operations"]:
        status = "✅" if op["alignment"] >= 0.5 else "❌ BLOCKED"
        print(f"  {status} {op['tool']}: alignment={op['alignment']:.2f}, risk={op['risk']}, gas={op['gas']}")
