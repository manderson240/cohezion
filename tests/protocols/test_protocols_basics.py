"""Greenfield tests for cohezion.protocols (Z7).

Targets the most-testable surfaces:
  - A2A: AgentCard serialisation, A2AServer task lifecycle, A2AClient construction
  - UCP: UCPCapability serialisation, handler discovery and invocation paths

Network-bound paths (httpx round-trips) are exercised via the in-process task
queue rather than real HTTP, and the CompoundExecutor import path falls through
to the documented echo behaviour when the executor isn't available.
"""

from __future__ import annotations

import asyncio
import json


from cohezion.protocols.a2a_server import (
    A2AClient,
    A2AMessage,
    A2AServer,
    A2ATask,
    AgentCard,
    TaskState,
)
from cohezion.protocols.ucp_capability_handler import (
    UCPCapability,
    UCPCapabilityHandler,
    UCPInvocationResult,
)


# -----------------------------------------------------------------------------
# A2A
# -----------------------------------------------------------------------------


def test_agent_card_default_serialisation_has_required_fields():
    card = AgentCard()
    payload = card.to_dict()
    for field in (
        "name",
        "description",
        "url",
        "version",
        "capabilities",
        "skills",
        "authentication",
        "defaultInputModes",
        "defaultOutputModes",
    ):
        assert field in payload
    # capabilities is the A2A-spec dict, not the raw skill list
    assert payload["capabilities"]["streaming"] is True
    # Skills are projected from the dataclass `capabilities` list
    skill_ids = {s["id"] for s in payload["skills"]}
    assert "simulation" in skill_ids


def test_agent_card_to_json_roundtrips():
    card = AgentCard(name="Custom", version="9.9.9")
    parsed = json.loads(card.to_json())
    assert parsed["name"] == "Custom"
    assert parsed["version"] == "9.9.9"


def test_a2a_server_get_agent_card_uses_provided_card():
    card = AgentCard(name="Specific")
    server = A2AServer(agent_card=card)
    assert server.get_agent_card()["name"] == "Specific"


def test_a2a_server_send_task_creates_task_and_routes():
    server = A2AServer()
    message = {"role": "user", "parts": [{"type": "text", "text": "hello a2a"}]}
    task = asyncio.run(server.send_task(message))
    assert isinstance(task, A2ATask)
    # Task is tracked
    assert task.id in server.tasks
    # Either the executor produced output (COMPLETED) or it failed (FAILED) —
    # both are acceptable terminal states; the SUBMITTED/WORKING in-flight
    # state should never be observed after the await returns.
    assert task.state in {TaskState.COMPLETED, TaskState.FAILED}
    # The agent message is appended after the user message
    assert len(task.messages) >= 2
    assert task.messages[0].role == "user"
    assert task.messages[-1].role == "agent"


def test_a2a_server_send_task_continues_existing_task():
    server = A2AServer()
    first = asyncio.run(
        server.send_task({"role": "user", "parts": [{"type": "text", "text": "one"}]})
    )
    second = asyncio.run(
        server.send_task(
            {"role": "user", "parts": [{"type": "text", "text": "two"}]},
            task_id=first.id,
        )
    )
    assert second.id == first.id
    assert len(server.tasks) == 1


def test_a2a_server_get_task_returns_none_for_unknown_id():
    server = A2AServer()
    result = asyncio.run(server.get_task("does-not-exist"))
    assert result is None


def test_a2a_server_cancel_task_only_cancels_working_tasks():
    server = A2AServer()
    # Manually inject a working task to test cancel path independently of routing.
    task = A2ATask(id="t1", state=TaskState.WORKING)
    server.tasks["t1"] = task
    assert asyncio.run(server.cancel_task("t1")) is True
    assert task.state == TaskState.CANCELED
    # A subsequent cancel returns False (not in WORKING any more)
    assert asyncio.run(server.cancel_task("t1")) is False
    # Unknown task -> False
    assert asyncio.run(server.cancel_task("nope")) is False


def test_a2a_message_dataclass_defaults():
    msg = A2AMessage(role="user", parts=[{"type": "text", "text": "x"}])
    assert msg.role == "user"
    assert msg.metadata == {}


def test_a2a_client_constructs_with_default_state():
    client = A2AClient()
    assert client.timeout == 30.0
    assert client._discovered_agents == {}


# -----------------------------------------------------------------------------
# UCP
# -----------------------------------------------------------------------------


def test_ucp_capability_to_dict_uses_camel_case_schema_keys():
    cap = UCPCapability(
        id="cohezion.skill.demo",
        name="demo",
        description="demo description",
    )
    payload = cap.to_dict()
    assert payload["id"] == "cohezion.skill.demo"
    assert payload["category"] == "ai_service"
    # Both schemas should be present with the camelCase UCP names.
    assert "inputSchema" in payload
    assert "outputSchema" in payload
    # Default pricing is free.
    assert payload["pricing"]["type"] == "free"


def test_ucp_handler_skips_when_skills_dir_missing(tmp_path):
    handler = UCPCapabilityHandler(skills_dir=str(tmp_path / "no-such-dir"))
    assert handler.capabilities == {}


def test_ucp_handler_loads_skill_with_skill_md(tmp_path):
    skills_dir = tmp_path / "skills"
    skill = skills_dir / "demo-skill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "# demo-skill\n\n## DOMAIN EXPERTISE\nDemo skill description line\n"
    )
    handler = UCPCapabilityHandler(skills_dir=str(skills_dir))
    assert "cohezion.skill.demo-skill" in handler.capabilities
    cap = handler.capabilities["cohezion.skill.demo-skill"]
    assert cap.name == "demo-skill"


def test_ucp_handler_discover_filters_by_query_and_category(tmp_path):
    skills_dir = tmp_path / "skills"
    a = skills_dir / "alpha"
    b = skills_dir / "beta"
    a.mkdir(parents=True)
    b.mkdir(parents=True)
    (a / "SKILL.md").write_text("# alpha\n\n## DOMAIN EXPERTISE\nAlpha helps with X\n")
    (b / "SKILL.md").write_text("# beta\n\n## DOMAIN EXPERTISE\nBeta helps with Y\n")
    handler = UCPCapabilityHandler(skills_dir=str(skills_dir))
    # No filter returns both
    assert len(handler.discover()) == 2
    # Query filter is substring against description
    matches = handler.discover(query="alpha helps")
    assert len(matches) == 1
    assert matches[0]["id"] == "cohezion.skill.alpha"
    # Category filter to a non-existent category returns empty
    assert handler.discover(category="nonexistent") == []


def test_ucp_invoke_unknown_capability_returns_error_result(tmp_path):
    handler = UCPCapabilityHandler(skills_dir=str(tmp_path / "missing"))
    result = asyncio.run(handler.invoke("cohezion.skill.unknown", {"prompt": "hi"}))
    assert isinstance(result, UCPInvocationResult)
    assert result.status == "error"
    assert "Unknown capability" in (result.error or "")


def test_ucp_invoke_missing_prompt_returns_error_result(tmp_path):
    skills_dir = tmp_path / "skills"
    skill = skills_dir / "demo"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# demo\n\n## DOMAIN EXPERTISE\nDemo\n")
    handler = UCPCapabilityHandler(skills_dir=str(skills_dir))
    result = asyncio.run(handler.invoke("cohezion.skill.demo", {}))
    assert result.status == "error"
    assert "prompt" in (result.error or "").lower()


def test_ucp_generate_manifest_includes_endpoints_and_capabilities(tmp_path):
    handler = UCPCapabilityHandler(
        skills_dir=str(tmp_path / "missing"),
        base_url="https://example.test",
    )
    manifest = handler.generate_manifest()
    assert manifest["provider"]["url"] == "https://example.test"
    assert "discover" in manifest["endpoints"]
    assert "invoke" in manifest["endpoints"]
    assert isinstance(manifest["capabilities"], list)


def test_ucp_write_manifest_creates_file(tmp_path):
    handler = UCPCapabilityHandler(skills_dir=str(tmp_path / "missing"))
    out = tmp_path / "out" / "ucp-manifest.json"
    written = handler.write_manifest(output_path=str(out))
    assert written == out
    assert out.exists()
    parsed = json.loads(out.read_text())
    assert parsed["name"] == "Cohezion Platform"
