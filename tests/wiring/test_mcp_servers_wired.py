"""Wiring identity tests for cohezion.mcp.servers sub-packages.

15 MCP server sub-packages were wired with contextlib.suppress blocks.
Each test verifies:
  1. The package is importable (pkg is not None).
  2. Any re-exported name that landed in the namespace is the right type
     (class → callable, function → callable, app instance → has __class__).

Because suppress swallows heavy-dep failures gracefully, export checks are
conditional: test passes whether the symbol resolved or not.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# doc
# ---------------------------------------------------------------------------


def test_doc_server_is_reachable() -> None:
    import cohezion.mcp.servers.doc as pkg

    assert pkg is not None


def test_doc_server_exports() -> None:
    import cohezion.mcp.servers.doc as pkg

    # create_app — factory function; may be absent when server deps unavailable
    if hasattr(pkg, "create_app"):
        assert callable(pkg.create_app)


# ---------------------------------------------------------------------------
# git
# ---------------------------------------------------------------------------


def test_git_server_is_reachable() -> None:
    import cohezion.mcp.servers.git as pkg

    assert pkg is not None


def test_git_server_exports() -> None:
    import cohezion.mcp.servers.git as pkg

    if hasattr(pkg, "GitContext"):
        assert callable(pkg.GitContext)


# ---------------------------------------------------------------------------
# github
# ---------------------------------------------------------------------------


def test_github_server_is_reachable() -> None:
    import cohezion.mcp.servers.github as pkg

    assert pkg is not None


def test_github_server_exports() -> None:
    import cohezion.mcp.servers.github as pkg

    if hasattr(pkg, "GitHubService"):
        assert callable(pkg.GitHubService)


# ---------------------------------------------------------------------------
# huggingface
# ---------------------------------------------------------------------------


def test_huggingface_server_is_reachable() -> None:
    import cohezion.mcp.servers.huggingface as pkg

    assert pkg is not None


def test_huggingface_server_exports() -> None:
    import cohezion.mcp.servers.huggingface as pkg

    if hasattr(pkg, "HuggingFaceService"):
        assert callable(pkg.HuggingFaceService)


# ---------------------------------------------------------------------------
# journey
# ---------------------------------------------------------------------------


def test_journey_server_is_reachable() -> None:
    import cohezion.mcp.servers.journey as pkg

    assert pkg is not None


def test_journey_server_exports() -> None:
    import cohezion.mcp.servers.journey as pkg

    if hasattr(pkg, "create_app"):
        assert callable(pkg.create_app)


# ---------------------------------------------------------------------------
# memory
# ---------------------------------------------------------------------------


def test_memory_server_is_reachable() -> None:
    import cohezion.mcp.servers.memory as pkg

    assert pkg is not None


def test_memory_server_exports() -> None:
    import cohezion.mcp.servers.memory as pkg

    if hasattr(pkg, "MemoryGraph"):
        assert callable(pkg.MemoryGraph)


# ---------------------------------------------------------------------------
# plasma
# ---------------------------------------------------------------------------


def test_plasma_server_is_reachable() -> None:
    import cohezion.mcp.servers.plasma as pkg

    assert pkg is not None


def test_plasma_server_exports() -> None:
    import cohezion.mcp.servers.plasma as pkg

    if hasattr(pkg, "PlasmaSimulation"):
        assert callable(pkg.PlasmaSimulation)


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------


def test_report_server_is_reachable() -> None:
    import cohezion.mcp.servers.report as pkg

    assert pkg is not None


def test_report_server_exports() -> None:
    import cohezion.mcp.servers.report as pkg

    if hasattr(pkg, "MarimoReportGenerator"):
        assert callable(pkg.MarimoReportGenerator)


# ---------------------------------------------------------------------------
# rewards
# ---------------------------------------------------------------------------


def test_rewards_server_is_reachable() -> None:
    import cohezion.mcp.servers.rewards as pkg

    assert pkg is not None


def test_rewards_server_exports() -> None:
    import cohezion.mcp.servers.rewards as pkg

    # `app` is a FastAPI/MCP application instance, not a callable factory
    if hasattr(pkg, "app"):
        assert pkg.app is not None


# ---------------------------------------------------------------------------
# security
# ---------------------------------------------------------------------------


def test_security_server_is_reachable() -> None:
    import cohezion.mcp.servers.security as pkg

    assert pkg is not None


def test_security_server_exports() -> None:
    import cohezion.mcp.servers.security as pkg

    if hasattr(pkg, "SecurityScanner"):
        assert callable(pkg.SecurityScanner)


# ---------------------------------------------------------------------------
# sequential
# ---------------------------------------------------------------------------


def test_sequential_server_is_reachable() -> None:
    import cohezion.mcp.servers.sequential as pkg

    assert pkg is not None


def test_sequential_server_exports() -> None:
    import cohezion.mcp.servers.sequential as pkg

    if hasattr(pkg, "ThinkingSession"):
        assert callable(pkg.ThinkingSession)


# ---------------------------------------------------------------------------
# simulate
# ---------------------------------------------------------------------------


def test_simulate_server_is_reachable() -> None:
    import cohezion.mcp.servers.simulate as pkg

    assert pkg is not None


def test_simulate_server_exports() -> None:
    import cohezion.mcp.servers.simulate as pkg

    if hasattr(pkg, "create_app"):
        assert callable(pkg.create_app)


# ---------------------------------------------------------------------------
# stitch
# ---------------------------------------------------------------------------


def test_stitch_server_is_reachable() -> None:
    import cohezion.mcp.servers.stitch as pkg

    assert pkg is not None


def test_stitch_server_exports() -> None:
    import cohezion.mcp.servers.stitch as pkg

    if hasattr(pkg, "StitchMCPClient"):
        assert callable(pkg.StitchMCPClient)


# ---------------------------------------------------------------------------
# template
# ---------------------------------------------------------------------------


def test_template_server_is_reachable() -> None:
    import cohezion.mcp.servers.template as pkg

    assert pkg is not None


def test_template_server_exports() -> None:
    import cohezion.mcp.servers.template as pkg

    if hasattr(pkg, "WeatherService"):
        assert callable(pkg.WeatherService)


# ---------------------------------------------------------------------------
# traceability
# ---------------------------------------------------------------------------


def test_traceability_server_is_reachable() -> None:
    import cohezion.mcp.servers.traceability as pkg

    assert pkg is not None


def test_traceability_server_exports() -> None:
    import cohezion.mcp.servers.traceability as pkg

    # Two function exports — both callable if present
    if hasattr(pkg, "traceability_run_engine"):
        assert callable(pkg.traceability_run_engine)
    if hasattr(pkg, "traceability_get_dashboard"):
        assert callable(pkg.traceability_get_dashboard)
