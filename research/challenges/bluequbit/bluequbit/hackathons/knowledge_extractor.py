#!/usr/bin/env python3
"""
Quantum Knowledge Extractor
Automated extraction of skills, patterns, and knowledge from quantum computing resources
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class QuantumSkill:
    """Reusable skill extracted from quantum computing resources"""

    id: str
    name: str
    category: str  # circuit, algorithm, optimization, debugging
    platform: str  # bluequbit, qiskit, braket, etc.
    difficulty: str  # beginner, intermediate, advanced
    description: str
    code_example: str
    prerequisites: List[str]
    use_cases: List[str]
    extracted_from: str
    created_at: str


@dataclass
class QuantumPattern:
    """Design or code pattern for quantum computing"""

    id: str
    name: str
    pattern_type: str  # design, architectural, code, anti-pattern
    description: str
    context: str
    solution: str
    applicability: List[str]
    examples: List[str]
    counter_examples: List[str]
    related_patterns: List[str]
    extracted_from: str


@dataclass
class QuantumKnowledge:
    """Conceptual knowledge about quantum computing"""

    id: str
    topic: str
    domain: str  # theory, implementation, application
    content: str
    source: str
    verified: bool
    tags: List[str]
    references: List[str]


class KnowledgeExtractor:
    """Extract and store quantum computing knowledge"""

    def __init__(self, vault_path: str, db_config: dict = None):
        self.vault_path = Path(vault_path)
        self.vault_path.mkdir(parents=True, exist_ok=True)
        self.extraction_count = 0
        self.skills: List[QuantumSkill] = []
        self.patterns: List[QuantumPattern] = []
        self.knowledge: List[QuantumKnowledge] = []

    def extract_skill_from_code(self, code: str, source: str, platform: str) -> QuantumSkill:
        """Extract skill from code example"""
        # Analyze code for skill identification
        skill = QuantumSkill(
            id=f"skill_{self.extraction_count:04d}",
            name=self._extract_skill_name(code),
            category=self._categorize_code(code),
            platform=platform,
            difficulty=self._assess_difficulty(code),
            description=self._extract_description(code),
            code_example=code,
            prerequisites=self._extract_prerequisites(code),
            use_cases=self._extract_use_cases(code),
            extracted_from=source,
            created_at=datetime.now().isoformat(),
        )
        self.skills.append(skill)
        self.extraction_count += 1
        return skill

    def extract_pattern(
        self, name: str, description: str, context: str, solution: str, source: str
    ) -> QuantumPattern:
        """Extract design pattern"""
        pattern = QuantumPattern(
            id=f"pattern_{self.extraction_count:04d}",
            name=name,
            pattern_type=self._classify_pattern(description),
            description=description,
            context=context,
            solution=solution,
            applicability=self._extract_applicability(description),
            examples=[],
            counter_examples=[],
            related_patterns=[],
            extracted_from=source,
        )
        self.patterns.append(pattern)
        self.extraction_count += 1
        return pattern

    def store_in_vault(self):
        """Store all extracted knowledge in Obsidian vault"""
        # Create directory structure
        (self.vault_path / "cerebellum" / "quantum" / "skills").mkdir(parents=True, exist_ok=True)
        (self.vault_path / "cerebellum" / "quantum" / "patterns").mkdir(parents=True, exist_ok=True)
        (self.vault_path / "cortex" / "quantum" / "concepts").mkdir(parents=True, exist_ok=True)

        # Store skills
        for skill in self.skills:
            self._write_skill_to_vault(skill)

        # Store patterns
        for pattern in self.patterns:
            self._write_pattern_to_vault(pattern)

        # Store knowledge
        for knowledge in self.knowledge:
            self._write_knowledge_to_vault(knowledge)

        # Update index
        self._update_vault_index()

    def _write_skill_to_vault(self, skill: QuantumSkill):
        """Write skill as markdown file in vault"""
        filepath = self.vault_path / "cerebellum" / "quantum" / "skills" / f"{skill.id}.md"
        content = f"""# {skill.name}

**Category:** {skill.category}  
**Platform:** {skill.platform}  
**Difficulty:** {skill.difficulty}  
**Source:** {skill.extracted_from}

## Description
{skill.description}

## Code Example
```python
{skill.code_example}
```

## Prerequisites
{chr(10).join(f"- {p}" for p in skill.prerequisites)}

## Use Cases
{chr(10).join(f"- {u}" for u in skill.use_cases)}

## Metadata
- **ID:** {skill.id}
- **Created:** {skill.created_at}
- **Tags:** #{skill.platform} #{skill.category} #skill
"""
        filepath.write_text(content)

    def _write_pattern_to_vault(self, pattern: QuantumPattern):
        """Write pattern as markdown file in vault"""
        filepath = self.vault_path / "cerebellum" / "quantum" / "patterns" / f"{pattern.id}.md"
        content = f"""# {pattern.name}

**Type:** {pattern.pattern_type}  
**Source:** {pattern.extracted_from}

## Description
{pattern.description}

## Context
{pattern.context}

## Solution
{pattern.solution}

## Applicability
{chr(10).join(f"- {a}" for a in pattern.applicability)}

## Examples
{chr(10).join(f"- {e}" for e in pattern.examples)}

## Related Patterns
{chr(10).join(f"- [[{r}]]" for r in pattern.related_patterns)}

## Metadata
- **ID:** {pattern.id}
- **Tags:** #{pattern.pattern_type} #pattern #quantum
"""
        filepath.write_text(content)

    def _write_knowledge_to_vault(self, knowledge: QuantumKnowledge):
        """Write knowledge as markdown file in vault"""
        filepath = self.vault_path / "cortex" / "quantum" / "concepts" / f"{knowledge.id}.md"
        content = f"""# {knowledge.topic}

**Domain:** {knowledge.domain}  
**Source:** {knowledge.source}  
**Verified:** {"✅" if knowledge.verified else "⚠️"}

## Content
{knowledge.content}

## References
{chr(10).join(f"- {r}" for r in knowledge.references)}

## Metadata
- **ID:** {knowledge.id}
- **Tags:** {" ".join(f"#{t}" for t in knowledge.tags)}
"""
        filepath.write_text(content)

    def _update_vault_index(self):
        """Update vault index files"""
        # Update skills index
        skills_index = self.vault_path / "cerebellum" / "quantum" / "skills" / "_index.md"
        skills_content = "# Quantum Skills Index\n\n"
        for skill in self.skills:
            skills_content += f"- [[{skill.id}]] - {skill.name} ({skill.platform})\n"
        skills_index.write_text(skills_content)

        # Update patterns index
        patterns_index = self.vault_path / "cerebellum" / "quantum" / "patterns" / "_index.md"
        patterns_content = "# Quantum Patterns Index\n\n"
        for pattern in self.patterns:
            patterns_content += f"- [[{pattern.id}]] - {pattern.name}\n"
        patterns_index.write_text(patterns_content)

    # Helper methods
    def _extract_skill_name(self, code: str) -> str:
        """Extract skill name from code"""
        # Look for function names or class names
        func_match = re.search(r"def ([a-zA-Z_][a-zA-Z0-9_]*)", code)
        class_match = re.search(r"class ([a-zA-Z_][a-zA-Z0-9_]*)", code)

        if func_match:
            return func_match.group(1).replace("_", " ").title()
        elif class_match:
            return class_match.group(1).replace("_", " ").title()
        else:
            return f"Quantum Skill {self.extraction_count}"

    def _categorize_code(self, code: str) -> str:
        """Categorize code into skill type"""
        if "run" in code.lower() and "circuit" in code.lower():
            return "execution"
        elif "optimize" in code.lower() or "transpile" in code.lower():
            return "optimization"
        elif "measure" in code.lower() or "counts" in code.lower():
            return "measurement"
        elif "error" in code.lower():
            return "error-mitigation"
        else:
            return "general"

    def _assess_difficulty(self, code: str) -> str:
        """Assess difficulty level from code complexity"""
        lines = code.strip().split("\n")
        non_empty = [l for l in lines if l.strip()]

        if len(non_empty) < 10:
            return "beginner"
        elif len(non_empty) < 30:
            return "intermediate"
        else:
            return "advanced"

    def _extract_description(self, code: str) -> str:
        """Extract description from docstrings/comments"""
        # Look for docstrings
        docstring_match = re.search(r'"""(.*?)"""', code, re.DOTALL)
        if docstring_match:
            return docstring_match.group(1).strip()[:200]

        # Look for comments
        comment_lines = [l for l in code.split("\n") if l.strip().startswith("#")]
        if comment_lines:
            return comment_lines[0].replace("#", "").strip()[:200]

        return f"Skill extracted from code example"

    def _extract_prerequisites(self, code: str) -> List[str]:
        """Extract prerequisites from imports"""
        imports = re.findall(r"(?:import|from) ([a-zA-Z_][a-zA-Z0-9_]*)", code)
        return list(set(imports))

    def _extract_use_cases(self, code: str) -> List[str]:
        """Extract use cases from code"""
        use_cases = []

        if "run" in code.lower():
            use_cases.append("Circuit execution")
        if "optimize" in code.lower():
            use_cases.append("Circuit optimization")
        if "measure" in code.lower():
            use_cases.append("Measurement and analysis")
        if "transpile" in code.lower():
            use_cases.append("Circuit transpilation")

        return use_cases if use_cases else ["General quantum programming"]

    def _classify_pattern(self, description: str) -> str:
        """Classify pattern type from description"""
        desc_lower = description.lower()

        if any(word in desc_lower for word in ["design", "structure", "architecture"]):
            return "design"
        elif any(word in desc_lower for word in ["avoid", "prevent", "anti"]):
            return "anti-pattern"
        elif any(word in desc_lower for word in ["code", "implementation"]):
            return "code"
        else:
            return "general"

    def _extract_applicability(self, description: str) -> List[str]:
        """Extract applicability from description"""
        # Common applicability patterns
        contexts = []

        if "circuit" in description.lower():
            contexts.append("Quantum circuit design")
        if "error" in description.lower():
            contexts.append("Error mitigation")
        if "optimization" in description.lower():
            contexts.append("Circuit optimization")
        if "measurement" in description.lower():
            contexts.append("Measurement strategies")

        return contexts if contexts else ["General quantum computing"]


# Example usage
if __name__ == "__main__":
    extractor = KnowledgeExtractor("/home/mike-anderson/vaults/cohezion-vault")

    # Example: Extract skill from BlueQubit code
    code_example = '''
import bluequbit
import qiskit

def solve_peaked_circuit(circuit_path):
    """Extract heavy output from peaked circuit using MPS simulation"""
    bq = bluequbit.init()
    
    with open(circuit_path) as f:
        qc = qiskit.QuantumCircuit.from_qasm_str(f.read())
    
    result = bq.run(qc, device='mps.cpu', shots=100000)
    counts = result.get_counts()
    
    return max(counts, key=counts.get)
'''

    skill = extractor.extract_skill_from_code(code_example, "BlueQubit Tutorial", "bluequbit")
    print(f"Extracted skill: {skill.name}")

    # Store in vault
    extractor.store_in_vault()
    print("Knowledge stored in vault")
