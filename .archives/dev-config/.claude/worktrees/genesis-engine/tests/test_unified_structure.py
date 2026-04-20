"""Tests for unified directory structure verification.

Tests that the "as above, so below" structural unification is complete.
"""

import sys
from pathlib import Path

import pytest

# Add src to path if not already there
SRC_PATH = Path(__file__).parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


class TestUnifiedKernelStructure:
    """Test unified kernel directory structure."""

    def test_kernels_directory_exists(self):
        """Verify unified kernels directory exists."""
        kernels_path = SRC_PATH / "cohezion" / "kernels"
        assert kernels_path.exists(), f"Kernels directory not found at {kernels_path}"

    def test_amd_subdirectories_exist(self):
        """Verify AMD kernel subdirectories exist."""
        amd_path = SRC_PATH / "cohezion" / "kernels" / "amd"
        assert amd_path.exists(), "AMD kernels directory not found"

        # Check subdirectories
        for kernel_type in ["moe", "gemm", "mla"]:
            kernel_path = amd_path / kernel_type
            assert kernel_path.exists(), f"{kernel_type} kernel directory not found"

    def test_nvidia_directory_exists(self):
        """Verify NVIDIA kernels directory exists (for future)."""
        nvidia_path = SRC_PATH / "cohezion" / "kernels" / "nvidia"
        assert nvidia_path.exists(), "NVIDIA kernels directory not found"

    def test_moe_kernel_files(self):
        """Verify MoE kernel files are present."""
        moe_path = SRC_PATH / "cohezion" / "kernels" / "amd" / "moe"
        required_files = ["task.py", "submission.py", "reference.py", "task.yml", "README.md"]
        for f in required_files:
            assert (moe_path / f).exists(), f"MoE kernel missing {f}"

    def test_gemm_kernel_files(self):
        """Verify GEMM kernel files are present."""
        gemm_path = SRC_PATH / "cohezion" / "kernels" / "amd" / "gemm"
        required_files = ["task.py", "submission.py", "reference.py", "task.yml"]
        for f in required_files:
            assert (gemm_path / f).exists(), f"GEMM kernel missing {f}"

    def test_mla_kernel_files(self):
        """Verify MLA kernel files are present."""
        mla_path = SRC_PATH / "cohezion" / "kernels" / "amd" / "mla"
        required_files = ["task.py", "submission.py", "reference.py", "task.yml", "README.md"]
        for f in required_files:
            assert (mla_path / f).exists(), f"MLA kernel missing {f}"

    def test_eval_and_utils_present(self):
        """Verify eval.py and utils.py are at kernels root."""
        kernels_path = SRC_PATH / "cohezion" / "kernels"
        assert (kernels_path / "eval.py").exists(), "eval.py not found at kernels root"
        assert (kernels_path / "utils.py").exists(), "utils.py not found at kernels root"


class TestUnifiedKSearchStructure:
    """Test unified ksearch directory structure."""

    def test_ksearch_directory_exists(self):
        """Verify unified ksearch directory exists."""
        ksearch_path = SRC_PATH / "cohezion" / "ksearch"
        assert ksearch_path.exists(), f"KSearch directory not found at {ksearch_path}"

    def test_ksearch_init_file(self):
        """Verify ksearch __init__.py exists."""
        init_path = SRC_PATH / "cohezion" / "ksearch" / "__init__.py"
        assert init_path.exists(), "KSearch __init__.py not found"

    def test_ksearch_tree_file(self):
        """Verify ksearch tree.py exists."""
        tree_path = SRC_PATH / "cohezion" / "ksearch" / "tree.py"
        assert tree_path.exists(), "KSearch tree.py not found"

    def test_ksearch_node_file(self):
        """Verify ksearch node.py exists."""
        node_path = SRC_PATH / "cohezion" / "ksearch" / "node.py"
        assert node_path.exists(), "KSearch node.py not found"

    def test_ksearch_trees_directory(self):
        """Verify ksearch trees directory and tree files exist."""
        trees_path = SRC_PATH / "cohezion" / "ksearch" / "trees"
        assert trees_path.exists(), "KSearch trees directory not found"

        # Check tree files
        for tree_type in ["gemm", "moe", "mla"]:
            tree_file = trees_path / f"{tree_type}_tree.json"
            assert tree_file.exists(), f"{tree_type}_tree.json not found"


class TestUnifiedConfigStructure:
    """Test unified config directory structure."""

    def test_unified_loader_exists(self):
        """Verify unified_loader.py exists."""
        loader_path = SRC_PATH / "cohezion" / "config" / "unified_loader.py"
        assert loader_path.exists(), "unified_loader.py not found"


class TestPathResolution:
    """Test that path resolution works correctly."""

    def test_ksearch_import(self):
        """Verify ksearch module can be imported."""
        try:
            from src.cohezion.ksearch import KernelTree, Node, NodeStatus, load_tree

            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import ksearch module: {e}")

    def test_node_creation(self):
        """Verify Node class works correctly."""
        from src.cohezion.ksearch import Node, NodeStatus

        node = Node(
            id="test_001",
            name="test_node",
            description="Test node",
            status=NodeStatus.OPEN,
            priority=0.5,
        )

        assert node.id == "test_001"
        assert node.name == "test_node"
        assert node.status == NodeStatus.OPEN
        assert node.is_leaf() is True

    def test_tree_creation(self):
        """Verify KernelTree class works correctly."""
        from src.cohezion.ksearch import KernelTree, Node, NodeStatus

        root = Node(
            id="root_001",
            name="root",
            status=NodeStatus.OPEN,
            priority=1.0,
        )
        child = Node(
            id="child_001",
            name="child",
            status=NodeStatus.OPEN,
            priority=0.5,
        )
        root.add_child(child)

        tree = KernelTree(
            version="1.0.0",
            kernel="test",
            hardware="MI355X",
            root=root,
        )

        assert tree.version == "1.0.0"
        assert tree.kernel == "test"
        assert tree.count_nodes() == 2
        assert tree.find_node("child_001") == child

    def test_load_gemm_tree(self):
        """Verify GEMM tree can be loaded."""
        from src.cohezion.ksearch import load_tree

        tree_path = SRC_PATH / "cohezion" / "ksearch" / "trees" / "gemm_tree.json"
        if tree_path.exists():
            tree = load_tree(tree_path)
            assert tree.kernel == "gemm"
            assert tree.version == "2.0.0"
            assert tree.count_nodes() > 0
