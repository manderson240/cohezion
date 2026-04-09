"""Cache test configuration.

Blocks sentence_transformers (and thus torch._C) from loading during test
collection. Without this, the first SentenceTransformerEncoder() instantiation
imports sentence_transformers, which eagerly loads torch._C into a process
that already has scipy/sklearn C extensions loaded — causing a BLAS allocator
conflict and segfault.

The individual test methods use patch("sentence_transformers.SentenceTransformer")
to provide specific mock behaviour; this conftest ensures the parent package
is already in sys.modules as a mock so no real import ever occurs.
"""

import sys
from unittest.mock import MagicMock

if "sentence_transformers" not in sys.modules:
    _mock_st = MagicMock()
    _mock_st.SentenceTransformer = MagicMock
    sys.modules["sentence_transformers"] = _mock_st
