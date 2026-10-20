"""splice: restated imports are a no-op; new imports and other statements are refused."""

from __future__ import annotations

import pytest

from cohezion.compound.autonomous_loop.act_loop import splice


SRC = "from typing import Any\nimport json\n\n\ndef f(x: Any) -> str:\n    return json.dumps(x)\n"
FIX = "def f(x: Any) -> str:\n    return json.dumps(x, sort_keys=True)\n"


def test_restated_existing_imports_are_ignored() -> None:
    with_imports = "from typing import Any\nimport json\n\n" + FIX
    assert splice(SRC, with_imports, anchor="f") == splice(SRC, FIX, anchor="f")
    assert "sort_keys=True" in splice(SRC, with_imports, anchor="f")


def test_new_import_is_refused_with_actionable_reason() -> None:
    with pytest.raises(ValueError, match=r"import inside the function body"):
        splice(SRC, "import re\n\n" + FIX, anchor="f")


def test_other_unsupported_statements_still_raise() -> None:
    with pytest.raises(ValueError, match="unsupported top-level statement"):
        splice(SRC, FIX + "\nprint('side effect')\n", anchor="f")
