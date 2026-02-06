import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from cohezion.universe.sandbox import ContainerizedUniverse


async def test_sandbox():
    sandbox = ContainerizedUniverse()
    print("Testing sandbox execution...")

    script = """
import os
print("Hello from Sandbox!")
print(f"Working Directory: {os.getcwd()}")
"""

    result = await sandbox.execute_code(script)

    print(f"Success: {result.success}")
    print(f"Exit Code: {result.exit_code}")
    print(f"STDOUT: {result.stdout.strip()}")
    print(f"STDERR: {result.stderr.strip()}")
    print(f"Duration: {result.duration:.2f}s")

    assert result.success is True
    assert "Hello from Sandbox!" in result.stdout


if __name__ == "__main__":
    asyncio.run(test_sandbox())
