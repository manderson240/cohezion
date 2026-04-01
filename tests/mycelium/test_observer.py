from unittest.mock import patch

import pytest

from cohezion.mycelium.observer import ChangeObserver


@pytest.fixture
def observer():
    return ChangeObserver()

def test_observer_initialization(observer):
    """Test that ChangeObserver initializes correctly."""
    assert observer is not None

def test_detect_modified_files_mock(observer):
    """Test detecting modified files using mocked git output."""
    with patch("subprocess.check_output") as mock_run:
        mock_run.return_value = b"src/cohezion/universe/engine.py\nsrc/cohezion/agents/base.py\n"
        files = observer.detect_modified_files(since_commit="HEAD~1")
        
        assert len(files) == 2
        assert "src/cohezion/universe/engine.py" in files
        assert "src/cohezion/agents/base.py" in files

def test_extract_diff_context(observer):
    """Test extracting diff context for a specific file."""
    with patch("subprocess.check_output") as mock_run:
        mock_run.return_value = b"""diff --git a/src/cohezion/universe/engine.py b/src/cohezion/universe/engine.py
index 12345..67890 100644
--- a/src/cohezion/universe/engine.py
+++ b/src/cohezion/universe/engine.py
@@ -10,3 +10,4 @@
 def existing_func():
     pass
 
+def new_func():
++    return "hello"
"""
        context = observer.extract_diff_context("src/cohezion/universe/engine.py", since_commit="HEAD~1")
        assert "new_func" in context
        assert "return \"hello\"" in context
