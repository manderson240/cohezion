import asyncio
import time

from cohezion.reliability.monitor import get_resource_monitor


async def mock_call(task_id: int, duration: float):
    monitor = get_resource_monitor()
    print(f"Task {task_id}: Waiting for capacity...")
    await monitor.wait_for_capacity()
    try:
        print(f"Task {task_id}: Slot acquired. Running for {duration}s...")
        await asyncio.sleep(duration)
    finally:
        print(f"Task {task_id}: Releasing slot.")
        monitor.release_capacity()


async def test_concurrency():
    # max_concurrency is 4 by default
    tasks = [
        mock_call(1, 1.0),
        mock_call(2, 1.0),
        mock_call(3, 1.0),
        mock_call(4, 1.0),
        mock_call(5, 1.0),
        mock_call(6, 1.0),
    ]
    start = time.perf_counter()
    await asyncio.gather(*tasks)
    end = time.perf_counter()
    print(f"\nTotal time: {end - start:.2f}s")
    print("Expected: Approx 2.0s (4 tasks in parallel, followed by 2 tasks)")


if __name__ == "__main__":
    asyncio.run(test_concurrency())
