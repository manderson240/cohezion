#!/usr/bin/env python3
"""
ASCENDED COHEZION - Agent Generator (Quarter on a String)
Creates new agents from minimal specifications.

Usage: python3 generate_agent.py "AgentName:task:capability"
"""

import sys
from pathlib import Path
from datetime import datetime

AGENT_TEMPLATE = '''"""
ASCENDED COHEZION - {name} Agent
Auto-generated: {timestamp}
"""

from dataclasses import dataclass
from typing import Any, Dict

@dataclass
class {name}State:
    """State for {name}"""
    intent: str = "{task}"
    capability: str = "{capability}"

class {name}Agent:
    """
    Agent for {task} with {capability} capability.
    Auto-generated via quarter-on-string strategy.
    """
    
    def __init__(self):
        self.state = {name}State()
        
    async def process(self, context: str) -> Dict[str, Any]:
        """Process {task}"""
        return {{
            "agent": "{name}",
            "task": "{task}",
            "capability": "{capability}",
            "status": "generated",
            "timestamp": "{timestamp}"
        }}

# Singleton
_agent = None

def get_{lower_name}_agent():
    global _agent
    if _agent is None:
        _agent = {name}Agent()
    return _agent
'''


def generate_agent(spec: str):
    """Generate agent from spec: Name:task:capability"""
    parts = spec.split(":")
    if len(parts) != 3:
        print("Usage: python3 generate_agent.py 'Name:task:capability'")
        sys.exit(1)

    name, task, capability = parts
    lower_name = name.lower()
    timestamp = datetime.now().isoformat()

    # Generate code
    code = AGENT_TEMPLATE.format(
        name=name,
        lower_name=lower_name,
        task=task,
        capability=capability,
        timestamp=timestamp,
    )

    # Write file
    output_dir = Path("/home/mike-anderson/dev/cohezion/src/cohezion/swarm/agents")
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{lower_name}.py"
    filepath = output_dir / filename
    filepath.write_text(code)

    print(f"✅ Generated: {filepath}")
    print(f"   Agent: {name}")
    print(f"   Task: {task}")
    print(f"   Capability: {capability}")
    print(f"   Lines: {len(code.splitlines())}")
    print(f"\n🚀 Next: python3 cohezion.py")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 generate_agent.py 'Name:task:capability'")
        print(
            "Example: python3 generate_agent.py 'DataMiner:extract:pattern_recognition'"
        )
        sys.exit(1)

    generate_agent(sys.argv[1])
