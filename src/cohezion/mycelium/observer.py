import logging
import shutil
import subprocess


logger = logging.getLogger(__name__)

# Resolve git executable at module load to avoid S607 partial-path warnings.
_GIT = shutil.which("git") or "/usr/bin/git"


class ChangeObserver:
    """
    Observes changes in the codebase to identify files that need test synthesis.
    """

    def __init__(self, root_dir: str = "."):
        self.root_dir = root_dir

    def detect_modified_files(self, since_commit: str = "HEAD~1") -> list[str]:
        """
        Uses git to identify files modified since a specific commit.

        Args:
            since_commit: The git reference to compare against.

        Returns:
            List[str]: List of paths to modified files.
        """
        try:
            output = subprocess.check_output(
                [_GIT, "diff", "--name-only", since_commit], cwd=self.root_dir
            ).decode("utf-8")

            files = [f.strip() for f in output.split("\n") if f.strip()]
            # Filter for .py files only for now
            py_files = [f for f in files if f.endswith(".py")]
            return py_files
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to detect modified files: {e}")
            return []

    def extract_diff_context(self, file_path: str, since_commit: str = "HEAD~1") -> str:
        """
        Extracts the git diff context for a specific file.

        Args:
            file_path: Path to the file.
            since_commit: The git reference to compare against.

        Returns:
            str: The diff content.
        """
        try:
            output = subprocess.check_output(
                [_GIT, "diff", since_commit, "--", file_path], cwd=self.root_dir
            ).decode("utf-8")
            return output
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to extract diff context for {file_path}: {e}")
            return ""
