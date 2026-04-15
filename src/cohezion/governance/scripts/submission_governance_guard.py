import ast
import os
from pathlib import Path
from cohezion.governance.guardian import Guardian

class SubmissionGovernanceGuard(Guardian):
    """
    Guard to enforce local rate limiting on competition submission scripts.
    
    Invariant: Any script that calls 'popcorn-cli submit' or performs a leaderboard 
    submission must include a call to 'check_rate_limit()'.
    """

    def __init__(self):
        super().__init__("submission-governance-guard")
        self.target_dir = self.project_root / "scripts/"
        self.submission_markers = ["popcorn-cli submit", "kaggle kernels push", "submit_to_leaderboard"]

    def scan_file(self, filepath: Path):
        try:
            content = filepath.read_text()
        except: return

        is_submission_script = any(marker in content for marker in self.submission_markers)
        if not is_submission_script:
            return

        # Check for check_rate_limit call
        try:
            tree = ast.parse(content)
            found_check = False
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func_name = ""
                    if isinstance(node.func, ast.Name): func_name = node.func.id
                    elif isinstance(node.func, ast.Attribute): func_name = node.func.attr
                    
                    if func_name == "check_rate_limit":
                        found_check = True
                        break
            
            if not found_check:
                self.log_violation(
                    "Submission script detected but 'check_rate_limit()' is missing. Enforce local 1-hour lock.",
                    location=str(filepath)
                )
        except Exception as e:
            self.logger.warning(f"AST parse failed for {filepath}: {e}")

    def run(self, auto_heal: bool = False) -> bool:
        if not self.target_dir.exists(): return True

        for root, _, files in os.walk(self.target_dir):
            for file in files:
                if file.endswith((".py", ".sh")):
                    self.scan_file(Path(root) / file)

        return len(self.violations) == 0

if __name__ == "__main__":
    guard = SubmissionGovernanceGuard()
    success = guard.run()
    guard.report()
    if not success:
        import sys
        sys.exit(1)
