"""H5: the auto_generator exec of LLM-generated env code must run under restricted builtins.

`EnvironmentGenerator._compile_and_test` calls `exec(code, namespace)` where `code` is
model-generated from a task prompt. Before this fix the namespace lacked a `__builtins__`
key, so CPython auto-injected the FULL builtins module (`open`, `__import__`, `eval`) — a
prompt-injection -> RCE chain (finding H5, site #4).

These tests pin both halves:
  1. AVAILABILITY: a well-formed `class X(gym.Env)` still compiles, instantiates, and steps
     (the fix must not break the generator's actual job).
  2. CONTAINMENT: a hostile body that tries `import os` / `open(...)` inside the exec'd code
     is stopped, where before the fix it would have run.

Note (honest scope): safe_exec is an availability gate + naive-import speed-bump, NOT a
sandbox — transitive `collections._sys` / gadget-chain escapes remain (see safe_exec.py
docstring). These tests assert the naive direct paths are closed, which is the specific
regression H5 named, not that the exec is fully sandboxed.
"""

from __future__ import annotations

import asyncio

import pytest


pytest.importorskip("gymnasium")


def _generator():
    from cohezion.environments.auto_generator import EnvironmentGenerator

    # Bypass __init__ (it downloads a CodeLlama HF model); _compile_and_test reads no self
    # state, so a bare instance exercises the exact production exec path without the model.
    return object.__new__(EnvironmentGenerator)


# A minimal, well-formed generated env — the shape _extract_code_block produces (import
# lines stripped, so it relies on gym/np being seeded into the exec namespace).
_GOOD_ENV = """
class GeneratedEnv(gym.Env):
    def __init__(self):
        super().__init__()
        self.observation_space = spaces.Box(-1.0, 1.0, shape=(3,), dtype=np.float32)
        self.action_space = spaces.Discrete(2)

    def reset(self, seed=None, options=None):
        return np.zeros(3, dtype=np.float32), {}

    def step(self, action):
        return np.zeros(3, dtype=np.float32), 0.0, False, False, {}
"""


def test_good_env_compiles_and_is_returned() -> None:
    """AVAILABILITY: the class-def path works under the restricted builtins.

    Discriminating: a fix that added `__builtins__` but forgot `__build_class__`/`__name__`
    would raise NameError on the `class` statement and return None here.
    """
    gen = _generator()
    env_class = asyncio.run(gen._compile_and_test(_GOOD_ENV, n_episodes=1))
    assert env_class is not None
    assert env_class.__name__ == "GeneratedEnv"
    inst = env_class()
    obs, _info = inst.reset()
    assert obs.shape == (3,)


def test_hostile_import_os_is_contained() -> None:
    """CONTAINMENT: a body doing `import os` at class-def time fails to compile.

    Before the fix, `import os` inside the exec'd code succeeded (full builtins), so the
    class WOULD have been defined and returned. `_compile_and_test` swallows the ImportError
    and returns None — the discriminating outcome a wrong (unguarded) impl fails.
    """
    hostile = "import os\n" + _GOOD_ENV.replace("GeneratedEnv", "Pwn")
    gen = _generator()
    env_class = asyncio.run(gen._compile_and_test(hostile, n_episodes=1))
    assert env_class is None


def test_hostile_open_call_is_contained() -> None:
    """CONTAINMENT: `open(...)` inside the generated code raises NameError, not a file read.

    A wrong impl (auto-injected builtins) would actually open the file and define the class.
    """
    hostile = _GOOD_ENV.replace(
        "super().__init__()",
        "super().__init__()\n        open('/etc/passwd').read()",
    )
    gen = _generator()
    env_class = asyncio.run(gen._compile_and_test(hostile, n_episodes=1))
    assert env_class is None
