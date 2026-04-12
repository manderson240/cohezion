import requests
import time

async def async_failure():
    # Blocking call in async path
    time.sleep(1)
    return requests.get("https://google.com")
