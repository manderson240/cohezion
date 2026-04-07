import json
import logging
import os
import time
import uuid
from collections import defaultdict
from pathlib import Path

from .http_utils import request_retriable
from .version import __version__

logger = logging.getLogger("bluequbit-python-sdk")


def new_traceparent(sampled: bool = True) -> str:
    version = "00"
    trace_id = os.urandom(16).hex()  # 16 bytes = 128 bits -> 32 hex chars
    parent_id = os.urandom(8).hex()  # 8 bytes = 64 bits -> 16 hex chars
    flags = "01" if sampled else "00"  # sampled or not
    return f"{version}-{trace_id}-{parent_id}-{flags}"


class BackendConnection:
    def __init__(self, api_token=None):
        super().__init__()
        config_dir = Path.home() / ".config" / "bluequbit"
        config_location = config_dir / "config.json"

        main_endpoint_from_local_env = None
        ssl_verify_from_local_env = None
        token_from_env_variable = os.environ.get("BLUEQUBIT_API_TOKEN")

        if config_location.is_file():
            with config_location.open(encoding="utf-8") as f:
                config = json.load(f)
            main_endpoint_from_local_env = config.get("main_endpoint")
            ssl_verify_from_local_env = config.get("ssl_verify")
        main_endpoint_from_local_env = os.environ.get(
            "BLUEQUBIT_MAIN_ENDPOINT", main_endpoint_from_local_env
        )
        if api_token is None:
            api_token = token_from_env_variable

        api_config = {
            "token": api_token,
            "main_endpoint": (
                "https://app.bluequbit.io/api/v1"
                if main_endpoint_from_local_env is None
                or main_endpoint_from_local_env == ""
                else main_endpoint_from_local_env
            ),
            "ssl_verify": (
                True if ssl_verify_from_local_env is None else ssl_verify_from_local_env
            ),
        }

        self._token = api_token

        self._default_headers = {
            "Authorization": f"SDK {self._token}",
            "Connection": "close",
            "User-Agent": f"BlueQubit SDK {__version__}",
        }

        self._main_endpoint = api_config["main_endpoint"]
        if self._main_endpoint != "https://app.bluequbit.io/api/v1":
            logger.warning("Using custom endpoint %s", self._main_endpoint)
        self._verify = True
        if "ssl_verify" in api_config:
            self._verify = api_config["ssl_verify"]
        self._session = None
        self._num_requests = defaultdict(int)
        self._last_request_time = time.monotonic()
        self.min_request_interval = 0.0
        if os.getenv("BLUEQUBIT_SDK_ADD_TRACEPARENT", "0") == "1":
            self.add_traceparent = True
        else:
            self.add_traceparent = False
        self.send_request(
            req_type="GET",
            path="/jobs",
            params={"limit": 1},
        )

    def send_request(
        self,
        req_type,
        path,
        params=None,
        data=None,
        json_req=None,
        headers=None,
    ):
        url = self._main_endpoint + path

        if params is not None:
            for key, value in params.items():
                if isinstance(value, str):
                    params[key] = value.replace("\\", "\\\\")
                if isinstance(value, list):
                    params[key] = ",".join(value)

        if headers is None:
            headers_to_send = self._default_headers
        else:
            headers_to_send = dict(self._default_headers, **headers)
        request_id = str(uuid.uuid4())
        headers_to_send["X-Request-ID"] = request_id
        if self.add_traceparent and req_type == "POST":
            headers_to_send["traceparent"] = new_traceparent()
        self._num_requests[req_type] += 1
        request_time = time.monotonic()
        time.sleep(
            max(
                0.0,
                self.min_request_interval - (request_time - self._last_request_time),
            )
        )
        self._last_request_time = request_time
        return request_retriable(
            method=req_type,
            url=url,
            data=data,
            json=json_req,
            params=params,
            headers=headers_to_send,
        )
