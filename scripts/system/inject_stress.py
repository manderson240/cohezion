import asyncio
from datetime import datetime

from cohezion.core.persistence.admin import DBAdmin


async def inject_stress():
    dba = DBAdmin()
    await dba.connect()

    # Inject a record with 0.05 dilation (Severe Stress)
    record = {
        "timestamp": datetime.now().isoformat(),
        "dilation_factor": 0.05,
        "hardware": {"cpu_percent": 95.5, "memory_percent": 88.0, "vram_percent": 92.0},
        "software": {"error": "timeout", "total_pending": 0},
    }

    await dba.client.create("system_pulse", record)
    print("✅ Injected Stress Record")
    await dba.close()


if __name__ == "__main__":
    asyncio.run(inject_stress())
