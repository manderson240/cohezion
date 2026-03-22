import asyncio
import json
import sys


try:
    import websockets
except ImportError:
    import os

    os.system("uv pip install websockets")
    import websockets


async def test_pulse():
    uri = "ws://localhost:8080/pulse"
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WS")
            # Listen for 3 messages
            for i in range(3):
                msg = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                data = json.loads(msg)
                print(f"✅ Received Pulse {i + 1}: {data['payload']['stats']}")
                brane = data["payload"]["brane"]
                if brane[5] > 0 or brane[6] > 0:
                    print(f"   Vectors Active: Stab={brane[5]:.2f} Ent={brane[6]:.2f}")

    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_pulse())
