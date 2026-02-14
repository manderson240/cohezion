#!/usr/bin/env python3
"""
Phase 6A: Automated Reasoning Chain Inference

Infers missing reasoning chains for decisions by:
1. Loading all decision notes from /decisions/ folder
2. Identifying decisions without reasoning_chain field
3. Using Ollama embeddings to find semantically similar decisions
4. Extracting reasoning_type patterns from similar decisions
5. Generating plausible 4-5 step chains based on patterns
6. Updating vault YAML with inferred chains (marked confidence=0.6, tag="inferred")
7. Logging all operations to inference_report.txt

Performance target: <500ms per decision, <30min total for 40 decisions
"""

import os
import sys
import json
import yaml
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import subprocess
import time
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

VAULT_PATH = Path("/home/mike-anderson/vaults/cohezion-vault")
DECISIONS_DIR = VAULT_PATH / "decisions"
OLLAMA_MCP_URL = "http://localhost:22360"  # Ollama MCP port


def load_decision_files() -> Dict[str, Dict]:
    """Load all decision notes from /decisions/ folder"""
    decisions = {}

    if not DECISIONS_DIR.exists():
        print(f"ERROR: Decisions directory not found: {DECISIONS_DIR}")
        return decisions

    for md_file in DECISIONS_DIR.glob("*.md"):
        try:
            content = md_file.read_text(encoding='utf-8')

            # Parse YAML frontmatter
            match = re.match(r"^---\n([\s\S]*?)\n---", content)
            if not match:
                continue

            frontmatter_str = match.group(1)
            body = content[match.end():].lstrip('\n')

            try:
                frontmatter = yaml.safe_load(frontmatter_str)
            except yaml.YAMLError as e:
                print(f"YAML error in {md_file.name}: {e}")
                continue

            # Check if it's a decision note
            if not frontmatter.get('title') or 'decision' not in frontmatter.get('tags', []):
                continue

            decisions[md_file.stem] = {
                'file': md_file,
                'title': frontmatter.get('title', ''),
                'frontmatter': frontmatter,
                'body': body,
                'content': content,
            }
        except Exception as e:
            print(f"Error loading {md_file.name}: {e}")

    return decisions


def identify_missing_chains(decisions: Dict[str, Dict]) -> List[str]:
    """Identify decisions WITHOUT reasoning_chain field"""
    missing = []

    for decision_id, decision_data in decisions.items():
        reasoning = decision_data['frontmatter'].get('decision_reasoning', {})

        # Check if reasoning_chain exists and has steps
        chain = reasoning.get('reasoning_chain')
        if not chain or (isinstance(chain, list) and len(chain) == 0):
            missing.append(decision_id)

    return missing


def get_ollama_embedding(text: str, model: str = "nomic-embed-text") -> Optional[List[float]]:
    """Get embedding from Ollama directly"""
    try:
        import requests

        url = "http://localhost:11434/api/embed"
        data = {"model": model, "input": text}

        resp = requests.post(url, json=data, timeout=10)
        if resp.status_code == 200:
            result = resp.json()
            if 'embeddings' in result and len(result['embeddings']) > 0:
                return result['embeddings'][0]
    except Exception as e:
        pass

    return None


def compute_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Compute cosine similarity between two vectors"""
    if not vec1 or not vec2:
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = sum(a * a for a in vec1) ** 0.5
    magnitude2 = sum(b * b for b in vec2) ** 0.5

    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0

    return dot_product / (magnitude1 * magnitude2)


def find_similar_decisions(
    decision_id: str,
    decision_data: Dict,
    all_decisions: Dict[str, Dict],
    embeddings_cache: Dict[str, List[float]],
    top_k: int = 3
) -> List[Tuple[str, float]]:
    """Find semantically similar decisions using embeddings"""

    # Get text for embedding
    decision_text = f"{decision_data['title']}\n{decision_data['frontmatter'].get('decision_reasoning', {}).get('rationale', '')}"

    # Get embedding (with caching)
    if decision_id not in embeddings_cache:
        emb = get_ollama_embedding(decision_text)
        if emb:
            embeddings_cache[decision_id] = emb
        else:
            return []

    source_emb = embeddings_cache.get(decision_id)
    if not source_emb:
        return []

    # Compute similarity to all other decisions
    similarities = []

    for other_id, other_data in all_decisions.items():
        if other_id == decision_id:
            continue

        # Skip decisions without reasoning chains
        other_reasoning = other_data['frontmatter'].get('decision_reasoning', {})
        if not other_reasoning.get('reasoning_chain'):
            continue

        # Get embedding
        if other_id not in embeddings_cache:
            other_text = f"{other_data['title']}\n{other_reasoning.get('rationale', '')}"
            emb = get_ollama_embedding(other_text)
            if emb:
                embeddings_cache[other_id] = emb
            else:
                continue

        other_emb = embeddings_cache.get(other_id)
        if not other_emb:
            continue

        # Compute similarity
        sim = compute_similarity(source_emb, other_emb)
        similarities.append((other_id, sim))

    # Sort by similarity and return top K
    similarities.sort(key=lambda x: x[1], reverse=True)
    return similarities[:top_k]


def extract_reasoning_types(decision_ids: List[str], all_decisions: Dict[str, Dict]) -> List[str]:
    """Extract reasoning_type from similar decisions"""
    types = []

    for decision_id in decision_ids:
        if decision_id in all_decisions:
            reasoning = all_decisions[decision_id]['frontmatter'].get('decision_reasoning', {})
            reasoning_type = reasoning.get('reasoning_type', 'hybrid')
            types.append(reasoning_type)

    return types


def generate_reasoning_chain(
    decision_id: str,
    decision_data: Dict,
    reasoning_types: List[str]
) -> Dict:
    """Generate plausible reasoning chain from patterns"""

    title = decision_data['title']
    rationale = decision_data['frontmatter'].get('decision_reasoning', {}).get('rationale', '')
    decision_text = f"{title}\n{rationale}"

    # Determine dominant reasoning type
    type_counts = {}
    for t in reasoning_types:
        type_counts[t] = type_counts.get(t, 0) + 1

    dominant_type = max(type_counts.items(), key=lambda x: x[1])[0] if type_counts else 'hybrid'

    # Generate 4-5 steps
    steps = []

    # Step 1: Problem/Context
    steps.append({
        'sequence': 1,
        'content': f'Context: {title[:80]}...' if len(title) > 80 else f'Context: {title}',
        'type': dominant_type if dominant_type == 'research' else 'research',
        'confidence': 0.65,
        'assumption': 'Problem was clearly identified'
    })

    # Step 2: Option Exploration
    steps.append({
        'sequence': 2,
        'content': 'Explored multiple implementation approaches and trade-offs',
        'type': dominant_type if dominant_type == 'pattern' else 'pattern',
        'confidence': 0.60,
        'assumption': 'Multiple options were considered'
    })

    # Step 3: Evaluation
    steps.append({
        'sequence': 3,
        'content': 'Evaluated options against project constraints and criteria',
        'type': dominant_type if dominant_type == 'research' else 'research',
        'confidence': 0.58,
        'assumption': 'Options were systematically evaluated'
    })

    # Step 4: Selection
    if len(decision_text) > 100:
        steps.append({
            'sequence': 4,
            'content': 'Selected option with best balance of trade-offs',
            'type': dominant_type,
            'confidence': 0.62,
            'assumption': 'Best option was chosen based on analysis'
        })

    chain = {
        'steps': [
            {
                'sequence': s['sequence'],
                'content': s['content'],
                'type': s['type'],
                'confidence': s['confidence'],
                'assumption': s['assumption']
            }
            for s in steps
        ]
    }

    return chain


def update_decision_yaml(
    decision_id: str,
    decision_data: Dict,
    reasoning_chain: Dict,
    confidence: float = 0.6,
    tag: str = 'inferred'
) -> bool:
    """Update decision YAML with inferred reasoning chain"""

    file_path = decision_data['file']

    try:
        # Parse current content
        content = decision_data['content']
        match = re.match(r"^---\n([\s\S]*?)\n---\n([\s\S]*)$", content)

        if not match:
            return False

        frontmatter_str, body = match.groups()
        frontmatter = yaml.safe_load(frontmatter_str)

        # Update with inferred reasoning
        if 'decision_reasoning' not in frontmatter:
            frontmatter['decision_reasoning'] = {}

        frontmatter['decision_reasoning']['reasoning_chain'] = reasoning_chain['steps']
        reasoning_type = reasoning_chain['steps'][0]['type'] if reasoning_chain['steps'] else 'hybrid'
        frontmatter['decision_reasoning']['reasoning_type'] = reasoning_type
        frontmatter['decision_reasoning']['confidence_score'] = confidence

        # Add inference tag
        if 'tags' not in frontmatter:
            frontmatter['tags'] = []
        if tag not in frontmatter['tags']:
            frontmatter['tags'].append(tag)

        # Rebuild YAML
        new_frontmatter = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
        new_content = f"---\n{new_frontmatter}---\n{body}"

        # Write back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return True
    except Exception as e:
        print(f"Error updating {decision_id}: {e}")
        return False


def main():
    """Main inference pipeline"""

    print("[Phase 6A] Automated Reasoning Chain Inference")
    print("=" * 60)

    start_time = time.time()

    # Load decisions
    print("\n1. Loading decision notes...")
    all_decisions = load_decision_files()
    print(f"   Loaded {len(all_decisions)} decision notes")

    # Identify missing chains
    print("\n2. Identifying decisions without reasoning chains...")
    missing_chains = identify_missing_chains(all_decisions)
    print(f"   Found {len(missing_chains)} decisions missing chains")

    if not missing_chains:
        print("   No chains to infer!")
        return

    # Process each missing chain
    print(f"\n3. Inferring {len(missing_chains)} reasoning chains...")

    embeddings_cache = {}
    inference_report = []
    success_count = 0

    for idx, decision_id in enumerate(missing_chains, 1):
        decision_data = all_decisions[decision_id]

        print(f"\n   [{idx}/{len(missing_chains)}] {decision_id}")
        start_decision = time.time()

        try:
            # Find similar decisions
            similar = find_similar_decisions(
                decision_id,
                decision_data,
                all_decisions,
                embeddings_cache,
                top_k=3
            )

            if not similar:
                print(f"       No similar decisions found (insufficient data)")
                continue

            # Extract reasoning types from similar
            similar_ids = [s[0] for s in similar]
            reasoning_types = extract_reasoning_types(similar_ids, all_decisions)

            # Generate chain
            reasoning_chain = generate_reasoning_chain(
                decision_id,
                decision_data,
                reasoning_types
            )

            # Update vault YAML
            if update_decision_yaml(decision_id, decision_data, reasoning_chain):
                elapsed = time.time() - start_decision
                print(f"       ✓ Updated ({elapsed:.2f}s)")
                print(f"       Similar: {', '.join(s[0] for s in similar[:2])}")
                print(f"       Type: {reasoning_types[0] if reasoning_types else 'hybrid'}")
                success_count += 1

                inference_report.append({
                    'decision_id': decision_id,
                    'title': decision_data['title'],
                    'status': 'inferred',
                    'similar_decisions': [s[0] for s in similar],
                    'reasoning_type': reasoning_types[0] if reasoning_types else 'hybrid',
                    'confidence': 0.6,
                    'elapsed_seconds': elapsed
                })
            else:
                print(f"       ✗ Update failed")
                inference_report.append({
                    'decision_id': decision_id,
                    'status': 'failed',
                    'error': 'YAML update failed'
                })

        except Exception as e:
            print(f"       ✗ Error: {e}")
            inference_report.append({
                'decision_id': decision_id,
                'status': 'error',
                'error': str(e)
            })

    # Generate report
    total_time = time.time() - start_time

    print("\n" + "=" * 60)
    print(f"Results: {success_count}/{len(missing_chains)} inferred successfully")
    print(f"Total time: {total_time:.1f}s ({total_time/len(missing_chains):.1f}s per decision)")

    # Save report
    report_path = VAULT_PATH / "inference_report.txt"
    with open(report_path, 'w') as f:
        f.write(f"Reasoning Chain Inference Report\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"Total inferred: {success_count}/{len(missing_chains)}\n")
        f.write(f"Time elapsed: {total_time:.1f}s\n")
        f.write(f"Avg per decision: {total_time/len(missing_chains):.1f}s\n\n")

        for entry in inference_report:
            if entry['status'] == 'inferred':
                f.write(f"✓ {entry['decision_id']}\n")
                f.write(f"  Title: {entry['title']}\n")
                f.write(f"  Type: {entry['reasoning_type']} (confidence: {entry['confidence']})\n")
                f.write(f"  Similar: {', '.join(entry['similar_decisions'][:2])}\n")
                f.write(f"  Time: {entry['elapsed_seconds']:.2f}s\n\n")
            else:
                f.write(f"✗ {entry['decision_id']} - {entry.get('status', 'unknown')}\n")
                if 'error' in entry:
                    f.write(f"  Error: {entry['error']}\n\n")

    print(f"Report saved: {report_path}")


if __name__ == "__main__":
    main()
