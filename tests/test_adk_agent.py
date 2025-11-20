from bmad.adk_agent.agent import get_current_time, root_agent


def test_agent_instantiation():
    assert root_agent.name == 'root_agent'
    assert len(root_agent.tools) == 1
    assert root_agent.tools[0] == get_current_time

def test_tool_execution():
    result = get_current_time("New York")
    assert result['city'] == "New York"
    assert result['status'] == "success"
