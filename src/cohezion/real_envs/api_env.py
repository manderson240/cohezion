"""Real API environment for executing actual HTTP requests.

Executes real API calls to live services with response capture,
authentication handling, and rate limiting.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from cohezion.real_envs.base import (
    RealAction,
    RealEnvironment,
    RealObservation,
    RealState,
    EnvironmentStep,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class APIAction(RealAction):
    """An API action (GET, POST, PUT, DELETE, etc.)."""

    # action_type values:
    # - "get": parameters={"url": str, "headers": dict, "params": dict}
    # - "post": parameters={"url": str, "headers": dict, "json": dict, "data": str}
    # - "put": parameters={"url": str, "headers": dict, "json": dict}
    # - "delete": parameters={"url": str, "headers": dict}
    # - "patch": parameters={"url": str, "headers": dict, "json": dict}
    # - "auth": parameters={"type": "bearer|basic|api_key", "credentials": dict}

    @classmethod
    def get(
        cls,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
    ) -> "APIAction":
        return cls(
            action_type="get",
            parameters={"url": url, "headers": headers or {}, "params": params or {}},
        )

    @classmethod
    def post(
        cls,
        url: str,
        headers: dict[str, str] | None = None,
        json_data: dict[str, Any] | None = None,
        data: str | None = None,
    ) -> "APIAction":
        return cls(
            action_type="post",
            parameters={
                "url": url,
                "headers": headers or {},
                "json": json_data,
                "data": data,
            },
        )

    @classmethod
    def put(
        cls,
        url: str,
        headers: dict[str, str] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> "APIAction":
        return cls(
            action_type="put",
            parameters={"url": url, "headers": headers or {}, "json": json_data},
        )

    @classmethod
    def delete(cls, url: str, headers: dict[str, str] | None = None) -> "APIAction":
        return cls(
            action_type="delete", parameters={"url": url, "headers": headers or {}}
        )

    @classmethod
    def patch(
        cls,
        url: str,
        headers: dict[str, str] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> "APIAction":
        return cls(
            action_type="patch",
            parameters={"url": url, "headers": headers or {}, "json": json_data},
        )

    @classmethod
    def set_auth_bearer(cls, token: str) -> "APIAction":
        return cls(action_type="auth", parameters={"type": "bearer", "token": token})

    @classmethod
    def set_auth_basic(cls, username: str, password: str) -> "APIAction":
        return cls(
            action_type="auth",
            parameters={"type": "basic", "username": username, "password": password},
        )

    @classmethod
    def set_auth_api_key(cls, key: str, header_name: str = "X-API-Key") -> "APIAction":
        return cls(
            action_type="auth",
            parameters={"type": "api_key", "key": key, "header_name": header_name},
        )


@dataclass
class APIObservation(RealObservation):
    """Observation from API after an action."""

    status_code: int = 0
    response_headers: dict[str, str] = field(default_factory=dict)
    response_body: str = ""
    response_json: dict[str, Any] | None = None
    request_url: str = ""
    request_method: str = ""
    latency_ms: float = 0.0
    rate_limited: bool = False

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base.update(
            {
                "status_code": self.status_code,
                "response_headers": dict(list(self.response_headers.items())[:20]),
                "response_body": self.response_body[:5000]
                if len(self.response_body) > 5000
                else self.response_body,
                "response_json": self.response_json,
                "request_url": self.request_url,
                "request_method": self.request_method,
                "latency_ms": self.latency_ms,
                "rate_limited": self.rate_limited,
            }
        )
        return base


@dataclass
class APIState(RealState):
    """Current state of the API environment."""

    base_url: str = ""
    auth_config: dict[str, Any] = field(default_factory=dict)
    default_headers: dict[str, str] = field(default_factory=dict)
    request_count: int = 0
    total_latency_ms: float = 0.0
    error_count: int = 0
    last_status_code: int = 0

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base.update(
            {
                "base_url": self.base_url,
                "auth_config": {
                    k: "***" if k in ("token", "password", "key") else v
                    for k, v in self.auth_config.items()
                },
                "default_headers": self.default_headers,
                "request_count": self.request_count,
                "total_latency_ms": self.total_latency_ms,
                "error_count": self.error_count,
                "last_status_code": self.last_status_code,
            }
        )
        return base


class APIEnvironment(RealEnvironment[APIAction, APIObservation, APIState]):
    """Real API environment with actual HTTP requests.

    Executes real API calls to live services with full request/response
    capture, authentication management, and rate limiting.

    Example:
        ```python
        env = APIEnvironment("Create and manage a GitHub repository")
        obs, state = env.reset()

        # Set authentication
        obs, reward, done, info = await env.step(
            APIAction.set_auth_bearer("ghp_xxx...")
        )

        # Create a repository
        obs, reward, done, info = await env.step(
            APIAction.post(
                "https://api.github.com/user/repos",
                json_data={"name": "test-repo", "private": False}
            )
        )

        # Get repository info
        obs, reward, done, info = await env.step(
            APIAction.get("https://api.github.com/repos/user/test-repo")
        )
        ```
    """

    def __init__(
        self,
        task_description: str,
        base_url: str | None = None,
        default_headers: dict[str, str] | None = None,
        timeout_seconds: float = 30.0,
        max_steps: int = 50,
        rate_limit_per_minute: int = 60,
        allowed_hosts: list[str] | None = None,
        blocked_hosts: list[str] | None = None,
    ):
        super().__init__(task_description, max_steps, "data/real_envs/api")

        self.base_url = base_url or ""
        self.default_headers = default_headers or {}
        self.timeout_seconds = timeout_seconds
        self.rate_limit_per_minute = rate_limit_per_minute
        self.allowed_hosts = set(allowed_hosts) if allowed_hosts else None
        self.blocked_hosts = set(blocked_hosts or [])

        self._client: httpx.AsyncClient | None = None
        self._auth_config: dict[str, Any] = {}
        self._request_times: list[float] = []  # For rate limiting

        self._state = APIState(
            state_type="api",
            base_url=self.base_url,
            default_headers=self.default_headers,
        )

        logger.info(f"APIEnvironment initialized with base_url: {self.base_url}")

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            headers = {**self.default_headers}

            # Apply auth if configured
            auth = None
            if self._auth_config.get("type") == "bearer":
                headers["Authorization"] = f"Bearer {self._auth_config['token']}"
            elif self._auth_config.get("type") == "basic":
                from httpx import BasicAuth

                auth = BasicAuth(
                    self._auth_config["username"], self._auth_config["password"]
                )
            elif self._auth_config.get("type") == "api_key":
                header_name = self._auth_config.get("header_name", "X-API-Key")
                headers[header_name] = self._auth_config["key"]

            self._client = httpx.AsyncClient(
                headers=headers,
                auth=auth,
                timeout=self.timeout_seconds,
                follow_redirects=True,
            )

        return self._client

    def reset(self, seed: int | None = None) -> tuple[APIObservation, APIState]:
        """Reset API environment to initial state."""
        self.current_step = 0
        self.trajectory = []
        self._is_done = False
        self._auth_config = {}
        self._request_times = []

        if self._client:
            # Close existing client
            asyncio.create_task(self._client.aclose())
            self._client = None

        state = APIState(
            state_type="api",
            base_url=self.base_url,
            default_headers=self.default_headers,
        )

        obs = APIObservation(
            success=True,
            data={"message": "API environment reset"},
        )

        self._state = state
        return obs, state

    async def step(
        self, action: APIAction
    ) -> tuple[APIObservation, float, bool, dict[str, Any]]:
        """Execute an API action."""
        start_time = time.time()

        success = True
        error_message = None
        obs_data: dict[str, Any] = {}

        # Rate limiting check
        await self._apply_rate_limit()

        try:
            if action.action_type == "auth":
                # Store auth config
                self._auth_config = {
                    k: v for k, v in action.parameters.items() if k != "action_type"
                }
                # Reset client to apply new auth
                if self._client:
                    await self._client.aclose()
                    self._client = None

                obs_data = {
                    "auth_configured": True,
                    "type": self._auth_config.get("type"),
                }

            elif action.action_type in ("get", "post", "put", "delete", "patch"):
                client = await self._get_client()

                url = action.parameters["url"]
                if self.base_url and not url.startswith(("http://", "https://")):
                    url = urljoin(self.base_url, url)

                # Security check
                self._check_host_allowed(url)

                headers = {**action.parameters.get("headers", {})}
                params = action.parameters.get("params", {})
                json_data = action.parameters.get("json")
                data = action.parameters.get("data")

                method = action.action_type.upper()

                request_kwargs = {
                    "headers": headers if headers else None,
                    "params": params if params else None,
                }

                if json_data is not None:
                    request_kwargs["json"] = json_data
                elif data is not None:
                    request_kwargs["data"] = data

                # Remove None values
                request_kwargs = {
                    k: v for k, v in request_kwargs.items() if v is not None
                }

                response = await client.request(method, url, **request_kwargs)

                latency_ms = (time.time() - start_time) * 1000
                self._request_times.append(time.time())

                # Try to parse JSON
                response_json = None
                try:
                    response_json = response.json()
                except:
                    pass

                obs = APIObservation(
                    success=response.status_code < 400,
                    data={},
                    error_message=None
                    if response.status_code < 400
                    else f"HTTP {response.status_code}",
                    latency_ms=latency_ms,
                    status_code=response.status_code,
                    response_headers=dict(response.headers),
                    response_body=response.text,
                    response_json=response_json,
                    request_url=str(response.request.url),
                    request_method=method,
                    rate_limited=response.status_code == 429,
                )

                # Update state
                self._state.request_count += 1
                self._state.total_latency_ms += latency_ms
                self._state.last_status_code = response.status_code

                if response.status_code >= 400:
                    self._state.error_count += 1

                # Check task completion
                is_complete, reward, metrics = self.evaluate_task()
                self._is_done = is_complete or self.current_step >= self.max_steps

                # Record step
                step = EnvironmentStep(
                    step_number=self.current_step,
                    action=action,
                    observation=obs,
                    state=self._state,
                    reward=reward,
                    done=self._is_done,
                    info={"latency_ms": latency_ms, **metrics},
                )
                self.trajectory.append(step)
                self.current_step += 1

                return obs, reward, self._is_done, metrics

            else:
                raise ValueError(f"Unknown action type: {action.action_type}")

        except Exception as e:
            success = False
            error_message = str(e)
            logger.error(f"API action failed: {e}")

            latency_ms = (time.time() - start_time) * 1000

            obs = APIObservation(
                success=False,
                data=obs_data,
                error_message=error_message,
                latency_ms=latency_ms,
                request_url=action.parameters.get("url", ""),
                request_method=action.action_type.upper()
                if action.action_type != "auth"
                else "AUTH",
            )

            self._state.error_count += 1

            is_complete, reward, metrics = self.evaluate_task()
            self._is_done = is_complete or self.current_step >= self.max_steps

            step = EnvironmentStep(
                step_number=self.current_step,
                action=action,
                observation=obs,
                state=self._state,
                reward=reward,
                done=self._is_done,
                info={"latency_ms": latency_ms, **metrics},
            )
            self.trajectory.append(step)
            self.current_step += 1

            return obs, reward, self._is_done, metrics

        # Handle non-HTTP actions (auth, etc.)
        latency_ms = (time.time() - start_time) * 1000

        obs = APIObservation(
            success=success,
            data=obs_data,
            error_message=error_message,
            latency_ms=latency_ms,
        )

        is_complete, reward, metrics = self.evaluate_task()
        self._is_done = is_complete or self.current_step >= self.max_steps

        step = EnvironmentStep(
            step_number=self.current_step,
            action=action,
            observation=obs,
            state=self._state,
            reward=reward,
            done=self._is_done,
            info={"latency_ms": latency_ms, **metrics},
        )
        self.trajectory.append(step)
        self.current_step += 1

        return obs, reward, self._is_done, metrics

    async def _apply_rate_limit(self):
        """Apply rate limiting to avoid overwhelming services."""
        now = time.time()

        # Remove old request times (older than 1 minute)
        self._request_times = [t for t in self._request_times if now - t < 60]

        # If at rate limit, wait
        if len(self._request_times) >= self.rate_limit_per_minute:
            oldest = min(self._request_times)
            wait_time = 60 - (now - oldest)
            if wait_time > 0:
                logger.warning(f"Rate limit hit, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)

    def _check_host_allowed(self, url: str) -> None:
        """Security check: ensure host is allowed."""
        parsed = urlparse(url)
        host = parsed.netloc

        if host in self.blocked_hosts:
            raise ValueError(f"Host {host} is blocked")

        if self.allowed_hosts and host not in self.allowed_hosts:
            raise ValueError(f"Host {host} is not in allowed list")

    def get_state(self) -> APIState:
        """Get current API state."""
        return self._state

    def evaluate_task(self) -> tuple[bool, float, dict[str, Any]]:
        """Evaluate if API task is complete."""
        if not self.trajectory:
            return False, 0.0, {}

        # Calculate metrics
        http_steps = [s for s in self.trajectory if s.action.action_type != "auth"]

        if not http_steps:
            success_rate = 1.0  # Only auth actions
        else:
            success_count = sum(1 for s in http_steps if s.observation.success)
            success_rate = success_count / len(http_steps)

        # Reward based on success rate and low latency
        avg_latency = self._state.total_latency_ms / max(self._state.request_count, 1)
        latency_penalty = min(avg_latency / 1000, 0.5)  # Penalty for slow requests

        reward = success_rate * 0.1 - latency_penalty * 0.05

        # Check for task-specific criteria
        is_complete = False

        metrics = {
            "steps_taken": len(self.trajectory),
            "success_rate": success_rate,
            "request_count": self._state.request_count,
            "error_count": self._state.error_count,
            "avg_latency_ms": avg_latency,
        }

        return is_complete, reward, metrics

    async def close(self):
        """Close HTTP client and cleanup."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("API client closed")
