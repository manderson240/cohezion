import io
import pytest
from rich.console import Console
from cohezion.journey.narrator import NarrativeEngine
from cohezion.journey.registry import get_journey_registry
import asyncio

def strip_ansi(text):
    import re
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

@pytest.mark.asyncio
async def test_narrative_rendering_no_raw_tags():
    """
    Vitrification Test: Ensures the NarrativeEngine does not leak raw Rich tags.
    """
    buffer = io.StringIO()
    console = Console(file=buffer, force_terminal=True, width=80)
    engine = NarrativeEngine(console=console)

    test_text = "[bold #f093fb]TEST VOYAGE[/bold #f093fb]"
    # We use a very fast speed for testing
    await engine.typewrite(test_text, speed=0)

    output = buffer.getvalue()
    # Ensure raw tags are NOT in the output
    assert "[bold" not in output
    assert "#f093fb" not in output
    # Ensure the plain text IS in the output
    assert "TEST VOYAGE" in strip_ansi(output)

@pytest.mark.asyncio
async def test_journey_registry_integrity():
    """
    Vitrification Test: Ensures all registered journeys are loadable.
    """
    registry = get_journey_registry()
    voyages = registry.list_voyages()

    assert "Gateway to Cohezion" in voyages
    assert "The HIHO Attractor" in voyages

    for name, data in voyages.items():
        assert data["description"]
        assert callable(data["entry_point"])

if __name__ == "__main__":
    # Internal runner for quick feedback
    async def run_tests():
        print("Running Vitrification suite...")
        try:
            await test_narrative_rendering_no_raw_tags()
            print("✅ test_narrative_rendering_no_raw_tags passed")
            await test_journey_registry_integrity()
            print("✅ test_journey_registry_integrity passed")
        except Exception as e:
            print(f"❌ Test failed: {e}")

    asyncio.run(run_tests())
