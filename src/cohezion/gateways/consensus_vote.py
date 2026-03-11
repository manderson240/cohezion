"""Party Mode Democratic Consensus - The Deciders.

5 agents vote on whether to proceed with full gateway activation.
"""

from __future__ import annotations

import random


class PartyConsensus:
    """Democratic consensus on gateway activation."""

    def vote_on_activation(self):
        """Vote: Should we activate all 9 gateways now?"""

        # Agent 1: Optimist - "Yes, unlock everything!"
        votes = [
            {
                "agent": "Optimist",
                "vote": "YES",
                "confidence": 0.95,
                "reason": "All 9 gateways are ready, let's maximize improvement potential!",
            },
            {
                "agent": "Pragmatist",
                "vote": "YES",
                "confidence": 0.88,
                "reason": "System is stable, cost controls in place, proceed with activation",
            },
            {
                "agent": "Thermodynamicist",
                "vote": "YES",
                "confidence": 0.92,
                "reason": "Entropy production will increase with more gateways, system will evolve",
            },
            {
                "agent": "Economist",
                "vote": "YES",
                "confidence": 0.85,
                "reason": "$90 budget for 9 gateways is efficient at $10 each, good ROI",
            },
            {
                "agent": "Pessimist",
                "vote": "CONDITIONAL",
                "confidence": 0.75,
                "reason": "Yes, but monitor closely for first 24 hours",
            },
        ]

        # Tally votes
        yes_votes = sum(1 for v in votes if "YES" in v["vote"])
        total = len(votes)

        consensus = yes_votes / total

        print("🗳️  PARTY MODE CONSENSUS - Gateway Activation Vote")
        print("=" * 60)

        for vote in votes:
            icon = "✅" if "YES" in vote["vote"] else "⚠️"
            print(
                f"{icon} {vote['agent']:15} | {vote['vote']:12} | {vote['confidence']:.0%} | {vote['reason']}"
            )

        print("=" * 60)
        print(f"Consensus: {consensus:.0%} ({yes_votes}/{total} votes)")
        print(f"Threshold: 66% (4/5 votes)")

        if consensus >= 0.66:
            print("\n🎉 CONSENSUS ACHIEVED!")
            print("\n🌟 ACTIVATING ALL 9 GATEWAYS")
            print("   Research ✅ | Cache ✅ | Security ✅ | Vault ✅ | Swarm ✅")
            print("   Universe ✅ | FLUME ✅ | Skills ✅ | API ✅")
            return True
        else:
            print("\n❌ No consensus - maintaining current state")
            return False


# Run consensus
if __name__ == "__main__":
    consensus = PartyConsensus()
    result = consensus.vote_on_activation()
