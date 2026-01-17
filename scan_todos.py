"""
TODO Scanner Script.

Scans the codebase for:
- TODO
- FIXME
- HACK
- "Next Steps" sections in Markdown

Outputs a formatted list of tasks.
"""

import os
import re
from pathlib import Path

def scan_codebase():
    base_path = Path(".")
    todo_pattern = re.compile(r'(TODO|FIXME|HACK|XXX):\s*(.*)', re.IGNORECASE)
    next_steps_pattern = re.compile(r'##\s*Next Steps', re.IGNORECASE)
    
    tasks = []
    
    # Exclude these dirs
    excludes = {'.git', '.venv', 'venv', '__pycache__', '.pytest_cache', '.cohezion', 'node_modules'}
    
    for root, dirs, files in os.walk(base_path):
        # Modify dirs in-place to exclude
        dirs[:] = [d for d in dirs if d not in excludes]
        
        for file in files:
            if not file.endswith(('.py', '.md', '.json', '.js', '.ts')):
                continue
                
            path = Path(root) / file
            
            try:
                content = path.read_text(errors='ignore')
                lines = content.splitlines()
                
                # Check for TODOs
                for i, line in enumerate(lines):
                    match = todo_pattern.search(line)
                    if match:
                        tag, text = match.groups()
                        # Clean up text
                        text = text.strip()
                        if len(text) > 5:
                            tasks.append(f"- [ ] {tag} ({path.name}:{i+1}): {text}")
                
                # Check for Next Steps sections in Markdown
                if file.endswith('.md'):
                    in_next_steps = False
                    for line in lines:
                        if next_steps_pattern.search(line):
                            in_next_steps = True
                            continue
                        
                        if in_next_steps:
                            if line.startswith('#'): # New section starts
                                in_next_steps = False
                            elif line.strip().startswith('- [ ]') or line.strip().startswith('- '):
                                text = line.strip().lstrip('- [ ]').lstrip('- ').strip()
                                if text and "Deploy to Cloud Run" not in text: # Filter known common ones
                                    tasks.append(f"- [ ] Next Step ({path.name}): {text}")
                                    
            except Exception as e:
                pass
                
    return tasks

if __name__ == "__main__":
    found_tasks = scan_codebase()
    
    print("# Refined Codebase Tasks\n")
    for task in found_tasks:
        print(task)
        
    # Append to .cohezion/tasks.md logic would go here, but printing first for review
