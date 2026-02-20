"""Real browser environment using Playwright.

Executes actual browser actions and captures DOM state, screenshots, and
network activity for training agents on real web tasks.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from cohezion.real_envs.base import (
    RealAction,
    RealEnvironment,
    RealObservation,
    RealState,
    EnvironmentStep,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BrowserAction(RealAction):
    """A browser action (click, type, navigate, etc.)."""

    # action_type values:
    # - "navigate": parameters={"url": str}
    # - "click": parameters={"selector": str, "x": float, "y": float}
    # - "type": parameters={"selector": str, "text": str, "clear_first": bool}
    # - "scroll": parameters={"direction": "up"|"down", "amount": int}
    # - "wait": parameters={"ms": int}
    # - "screenshot": parameters={}
    # - "extract": parameters={"selector": str, "attribute": str|null}

    @classmethod
    def navigate(cls, url: str) -> "BrowserAction":
        return cls(action_type="navigate", parameters={"url": url})

    @classmethod
    def click(
        cls, selector: str | None = None, x: float | None = None, y: float | None = None
    ) -> "BrowserAction":
        params = {}
        if selector:
            params["selector"] = selector
        if x is not None and y is not None:
            params["x"] = x
            params["y"] = y
        return cls(action_type="click", parameters=params)

    @classmethod
    def type_text(
        cls, selector: str, text: str, clear_first: bool = True
    ) -> "BrowserAction":
        return cls(
            action_type="type",
            parameters={"selector": selector, "text": text, "clear_first": clear_first},
        )

    @classmethod
    def scroll(cls, direction: str = "down", amount: int = 300) -> "BrowserAction":
        return cls(
            action_type="scroll", parameters={"direction": direction, "amount": amount}
        )

    @classmethod
    def wait(cls, milliseconds: int = 1000) -> "BrowserAction":
        return cls(action_type="wait", parameters={"ms": milliseconds})

    @classmethod
    def screenshot(cls) -> "BrowserAction":
        return cls(action_type="screenshot", parameters={})

    @classmethod
    def extract(cls, selector: str, attribute: str | None = None) -> "BrowserAction":
        return cls(
            action_type="extract",
            parameters={"selector": selector, "attribute": attribute},
        )


@dataclass
class BrowserObservation(RealObservation):
    """Observation from browser after an action."""

    url: str = ""
    title: str = ""
    dom_structure: dict[str, Any] = field(default_factory=dict)
    screenshot_path: str | None = None
    extracted_text: str | None = None
    network_requests: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base.update(
            {
                "url": self.url,
                "title": self.title,
                "dom_structure": self.dom_structure,
                "screenshot_path": self.screenshot_path,
                "extracted_text": self.extracted_text,
                "network_requests": self.network_requests,
            }
        )
        return base


@dataclass
class BrowserState(RealState):
    """Current state of the browser."""

    url: str = ""
    title: str = ""
    viewport_size: dict[str, int] = field(
        default_factory=lambda: {"width": 1280, "height": 720}
    )
    scroll_position: dict[str, int] = field(default_factory=lambda: {"x": 0, "y": 0})
    interactive_elements: list[dict] = field(default_factory=list)
    page_source_hash: str = ""
    cookies: list[dict] = field(default_factory=list)
    local_storage: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base.update(
            {
                "url": self.url,
                "title": self.title,
                "viewport_size": self.viewport_size,
                "scroll_position": self.scroll_position,
                "interactive_elements": self.interactive_elements,
                "page_source_hash": self.page_source_hash,
                "cookies": self.cookies,
                "local_storage": self.local_storage,
            }
        )
        return base


class BrowserEnvironment(
    RealEnvironment[BrowserAction, BrowserObservation, BrowserState]
):
    """Real browser environment using Playwright.

    Executes actual browser actions on real websites with full
    DOM introspection and screenshot capture.

    Example:
        ```python
        env = BrowserEnvironment("Search for Python tutorials on Google")
        obs, state = env.reset()

        # Navigate to Google
        obs, reward, done, info = await env.step(BrowserAction.navigate("https://google.com"))

        # Type search query
        obs, reward, done, info = await env.step(
            BrowserAction.type_text('input[name="q"]', "Python tutorials")
        )

        # Click search button
        obs, reward, done, info = await env.step(
            BrowserAction.click('input[type="submit"]')
        )
        ```
    """

    def __init__(
        self,
        task_description: str,
        headless: bool = True,
        screenshot_dir: str = "data/real_envs/browser/screenshots",
        max_steps: int = 50,
        allowed_domains: list[str] | None = None,
        blocked_domains: list[str] | None = None,
    ):
        super().__init__(task_description, max_steps, "data/real_envs/browser")

        self.headless = headless
        self.screenshot_dir = Path(screenshot_dir)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

        self.allowed_domains = set(allowed_domains) if allowed_domains else None
        self.blocked_domains = set(blocked_domains or ["malicious-site.com"])

        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

        self._last_screenshot: str | None = None

    async def _init_browser(self):
        """Initialize Playwright browser instance."""
        if self._page is not None:
            return

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError(
                "Playwright not installed. Run: pip install playwright && playwright install"
            )

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.headless)
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        )

        # Block unwanted domains
        await self._context.route("**/*", self._route_handler)

        self._page = await self._context.new_page()
        logger.info("Browser initialized")

    async def _route_handler(self, route):
        """Handler to block unwanted domains."""
        url = route.request.url
        domain = urlparse(url).netloc

        if domain in self.blocked_domains:
            await route.abort("blockedbyclient")
            return

        if self.allowed_domains and domain not in self.allowed_domains:
            logger.warning(f"Blocking unallowed domain: {domain}")
            await route.abort("blockedbyclient")
            return

        await route.continue_()

    def reset(self, seed: int | None = None) -> tuple[BrowserObservation, BrowserState]:
        """Reset browser to initial blank state."""
        # Note: This is synchronous, actual browser init happens async
        obs = BrowserObservation(
            success=True,
            data={
                "message": "Browser reset - call reset_async() for actual initialization"
            },
        )
        state = BrowserState(state_type="browser")
        self._state = state
        return obs, state

    async def reset_async(
        self, seed: int | None = None
    ) -> tuple[BrowserObservation, BrowserState]:
        """Async reset - actually initializes browser."""
        await self._init_browser()

        if self._page:
            await self._page.goto("about:blank")

        self.current_step = 0
        self.trajectory = []
        self._is_done = False

        state = await self._capture_state()
        obs = BrowserObservation(
            success=True,
            url=state.url,
            title=state.title,
        )

        self._state = state
        return obs, state

    async def step(
        self, action: BrowserAction
    ) -> tuple[BrowserObservation, float, bool, dict[str, Any]]:
        """Execute a browser action."""
        start_time = time.time()

        if self._page is None:
            await self._init_browser()

        success = True
        error_message = None
        data: dict[str, Any] = {}

        try:
            if action.action_type == "navigate":
                url = action.parameters.get("url", "")
                await self._page.goto(url, wait_until="domcontentloaded")
                data["navigated_to"] = url

            elif action.action_type == "click":
                selector = action.parameters.get("selector")
                x = action.parameters.get("x")
                y = action.parameters.get("y")

                if selector:
                    await self._page.click(selector)
                    data["clicked_selector"] = selector
                elif x is not None and y is not None:
                    await self._page.mouse.click(x, y)
                    data["clicked_at"] = {"x": x, "y": y}
                else:
                    raise ValueError("Click requires selector or x,y coordinates")

            elif action.action_type == "type":
                selector = action.parameters["selector"]
                text = action.parameters["text"]
                clear_first = action.parameters.get("clear_first", True)

                if clear_first:
                    await self._page.fill(selector, "")
                await self._page.fill(selector, text)
                data["typed_text"] = text[:50] + "..." if len(text) > 50 else text

            elif action.action_type == "scroll":
                direction = action.parameters.get("direction", "down")
                amount = action.parameters.get("amount", 300)

                if direction == "down":
                    await self._page.evaluate(f"window.scrollBy(0, {amount})")
                else:
                    await self._page.evaluate(f"window.scrollBy(0, -{amount})")
                data["scrolled"] = f"{direction} by {amount}px"

            elif action.action_type == "wait":
                ms = action.parameters.get("ms", 1000)
                await asyncio.sleep(ms / 1000)
                data["waited_ms"] = ms

            elif action.action_type == "screenshot":
                screenshot_path = (
                    self.screenshot_dir
                    / f"step_{self.current_step}_{int(time.time())}.png"
                )
                await self._page.screenshot(path=str(screenshot_path))
                self._last_screenshot = str(screenshot_path)
                data["screenshot_path"] = str(screenshot_path)

            elif action.action_type == "extract":
                selector = action.parameters["selector"]
                attribute = action.parameters.get("attribute")

                if attribute:
                    value = await self._page.get_attribute(selector, attribute)
                    data["extracted_attribute"] = value
                else:
                    text = await self._page.text_content(selector)
                    data["extracted_text"] = text[:500] if text else None

            else:
                raise ValueError(f"Unknown action type: {action.action_type}")

        except Exception as e:
            success = False
            error_message = str(e)
            logger.error(f"Browser action failed: {e}")

        latency_ms = (time.time() - start_time) * 1000

        # Capture new state
        state = await self._capture_state()

        obs = BrowserObservation(
            success=success,
            data=data,
            error_message=error_message,
            latency_ms=latency_ms,
            url=state.url,
            title=state.title,
            screenshot_path=self._last_screenshot,
        )

        # Check if task complete
        is_complete, reward, metrics = self.evaluate_task()
        self._is_done = is_complete or self.current_step >= self.max_steps

        # Record step
        step = EnvironmentStep(
            step_number=self.current_step,
            action=action,
            observation=obs,
            state=state,
            reward=reward,
            done=self._is_done,
            info={"latency_ms": latency_ms, **metrics},
        )
        self.trajectory.append(step)
        self.current_step += 1

        return obs, reward, self._is_done, metrics

    async def _capture_state(self) -> BrowserState:
        """Capture current browser state."""
        if self._page is None:
            return BrowserState(state_type="browser")

        # Get basic page info
        url = self._page.url
        title = await self._page.title()

        # Get viewport and scroll position
        viewport = await self._page.viewport_size()
        scroll_pos = await self._page.evaluate(
            "() => ({x: window.scrollX, y: window.scrollY})"
        )

        # Get interactive elements
        interactive = await self._page.query_selector_all(
            'a, button, input, textarea, select, [role="button"], [onclick]'
        )
        elements = []
        for i, el in enumerate(interactive[:50]):  # Limit to first 50
            try:
                tag = await el.evaluate("el => el.tagName.toLowerCase()")
                text = await el.text_content()
                clickable = await el.is_visible()
                bbox = await el.bounding_box()
                elements.append(
                    {
                        "index": i,
                        "tag": tag,
                        "text": (text or "")[:50],
                        "clickable": clickable,
                        "bbox": bbox,
                    }
                )
            except:
                pass

        # Hash of page source for change detection
        content = await self._page.content()
        page_hash = hash(content) % (2**32)

        state = BrowserState(
            state_type="browser",
            url=url,
            title=title,
            viewport_size=viewport or {"width": 1280, "height": 720},
            scroll_position=scroll_pos,
            interactive_elements=elements,
            page_source_hash=str(page_hash),
        )

        self._state = state
        return state

    def get_state(self) -> BrowserState:
        """Get current browser state."""
        return self._state or BrowserState(state_type="browser")

    def evaluate_task(self) -> tuple[bool, float, dict[str, Any]]:
        """Evaluate if browser task is complete."""
        # This is task-specific - base implementation returns neutral
        # Subclasses or task definitions should override this

        if not self.trajectory:
            return False, 0.0, {}

        # Default: reward based on success rate
        success_rate = sum(1 for s in self.trajectory if s.observation.success) / len(
            self.trajectory
        )
        reward = success_rate * 0.1  # Small reward for each successful step

        # Check for task-specific completion criteria
        # (would be overridden by task evaluators)
        is_complete = False

        metrics = {
            "steps_taken": len(self.trajectory),
            "success_rate": success_rate,
            "final_url": self._state.url if self._state else None,
        }

        return is_complete, reward, metrics

    async def close(self):
        """Close browser and cleanup resources."""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Browser closed")
