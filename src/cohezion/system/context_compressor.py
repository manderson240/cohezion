
import os
import ast
import logging
from pathlib import Path
from typing import List, Dict

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class ContextCompressor:
    """
    Sovereign Memory Agent.
    Compresses the codebase into a high-density Markdown artifact.
    """
    
    OUTPUT_FILE = Path("SOVEREIGN_CONTEXT.md")
    SOURCE_DIR = Path("src/cohezion")
    IGNORE_DIRS = {"__pycache__", "tests", "migrations", "auto_generated"}
    
    def __init__(self):
        self.context = []

    def compress(self):
        """Walks the source tree and compresses context."""
        logger.info("🧠 ContextCompressor: Starting compression...")
        
        self.context.append("# SOVEREIGN CONTEXT")
        self.context.append(f"**Generated**: {os.popen('date').read().strip()}\n")
        
        for root, dirs, files in os.walk(self.SOURCE_DIR):
            # Prune ignored directories
            dirs[:] = [d for d in dirs if d not in self.IGNORE_DIRS]
            
            for file in files:
                if file.endswith(".py") and not file.startswith("__"):
                    path = Path(root) / file
                    self._process_file(path)
                    
        self.OUTPUT_FILE.write_text("\n".join(self.context))
        logger.info(f"✅ Squeezed codebase into {self.OUTPUT_FILE} ({self.OUTPUT_FILE.stat().st_size} bytes)")

    def _process_file(self, path: Path):
        """Extracts signatures and docstrings using AST."""
        try:
            content = path.read_text(encoding='utf-8', errors='ignore')
            tree = ast.parse(content)
            
            try:
                rel_path = path.resolve().relative_to(Path.cwd().resolve())
            except ValueError:
                rel_path = path  # Fallback
            
            self.context.append(f"\n## `{rel_path}`")
            
            # Module Docstring
            if ast.get_docstring(tree):
                doc = ast.get_docstring(tree).split('\n')[0] # First line only
                self.context.append(f"> {doc}")
                
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    self.context.append(f"- **class** `{node.name}`")
                    if ast.get_docstring(node):
                        self.context.append(f"  - *{ast.get_docstring(node).splitlines()[0]}*")
                        
                elif isinstance(node, ast.FunctionDef):
                    # Only show public methods/functions
                    if not node.name.startswith("_"):
                        args = [a.arg for a in node.args.args if a.arg != 'self']
                        sig = f"{node.name}({', '.join(args)})"
                        self.context.append(f"- `def {sig}`")
                        
        except Exception as e:
            logger.warning(f"Failed to parse {path}: {e}")

if __name__ == "__main__":
    compressor = ContextCompressor()
    compressor.compress()
