import asyncio
import os
import tempfile

from playwright.async_api import async_playwright


class CohezionBrowserAgent:
    """
    Native Playwright-based browser agent for Cohezion.
    Bypasses single-instance locks by using isolated contexts and unique user data directories.
    """

    def __init__(self, headless=True):
        self.headless = headless
        self._playwright = None
        self._browser = None

    async def start(self):
        self._playwright = await async_playwright().start()
        # Using launch_persistent_context to ensure isolation and bypass locks
        self.user_data_dir = tempfile.mkdtemp(prefix="cohezion_browser_")
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=self.headless,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        return self._context

    async def navigate(self, url):
        if not hasattr(self, "_context"):
            await self.start()

        page = await self._context.new_page()
        await page.goto(url, wait_until="networkidle")
        return page

    async def capture_screenshot(self, url, output_path):
        page = await self.navigate(url)
        await page.screenshot(path=output_path)
        await page.close()
        return output_path

    async def close(self):
        if hasattr(self, "_context"):
            await self._context.close()
        if self._playwright:
            await self._playwright.stop()

        # Cleanup temp dir
        if hasattr(self, "user_data_dir") and os.path.exists(self.user_data_dir):
            import shutil

            shutil.rmtree(self.user_data_dir, ignore_errors=True)


async def main():
    # Simple self-test
    agent = CohezionBrowserAgent(headless=True)
    try:
        print("Starting Cohezion Browser Agent...")
        await agent.start()
        print(f"Isolated context started in {agent.user_data_dir}")

        url = "http://localhost/research"
        output = "browser_test_screenshot.png"
        print(f"Navigating to {url} and capturing screenshot...")
        await agent.capture_screenshot(url, output)
        print(f"Screenshot saved to {output}")

    finally:
        await agent.close()
        print("Agent closed.")


if __name__ == "__main__":
    asyncio.run(main())
