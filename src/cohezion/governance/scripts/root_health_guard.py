#!/usr/bin/env python3
"""Root Health Guard - Dogfooding the archaeology skill.

Prevents re-accumulation of root clutter by failing CI when thresholds exceeded.
"""
import os
import sys
from pathlib import Path


def check_root_health():
    """Verify root item count within acceptable bounds."""
    root = Path('.')
    
    # Count non-hidden items
    items = [f for f in root.iterdir() 
             if not f.name.startswith('.') 
             and f.name not in {'.git', '.venv', '.hermes'}]
    
    count = len(items)
    
    # Thresholds from archaeology skill
    WARNING_THRESHOLD = 50
    ERROR_THRESHOLD = 75
    
    print(f"Root items: {count}")
    print(f"Warning threshold: {WARNING_THRESHOLD}")
    print(f"Error threshold: {ERROR_THRESHOLD}")
    
    # Categorize for diagnostic
    categories = {
        'essential': [],
        'suspicious': [],
    }
    
    essential = {'README.md', 'LICENSE', 'AGENTS.md', 'src', 'tests', 'docs',
                 'Makefile', 'pyproject.toml', 'uv.lock', 'data', 'benchmarks',
                 'scripts', 'CHANGELOG.md', 'CONTRIBUTING.md', 'SECURITY.md'}
    
    for item in items:
        if item.name in essential:
            categories['essential'].append(item.name)
        else:
            categories['suspicious'].append(item.name)
    
    if categories['suspicious']:
        print(f"\n⚠️  Non-essential items detected:")
        for item in categories['suspicious'][:10]:
            print(f"  - {item}")
        if len(categories['suspicious']) > 10:
            print(f"  ... and {len(categories['suspicious']) - 10} more")
    
    if count > ERROR_THRESHOLD:
        print(f"\n❌ FAILURE: Root has {count} items (max {ERROR_THRESHOLD})")
        print("   Run: make archaeology")
        return 1
    elif count > WARNING_THRESHOLD:
        print(f"\n⚠️  WARNING: Root has {count} items (target <{WARNING_THRESHOLD})")
        return 0
    else:
        print(f"\n✅ Root health: {count} items (good)")
        return 0


if __name__ == '__main__':
    sys.exit(check_root_health())
