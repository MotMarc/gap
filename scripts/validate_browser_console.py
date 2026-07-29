"""Instrument the live GAP frontend through Chrome DevTools Protocol."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import websockets

REQUIRED_RESOURCE_TYPES = {
    "Document",
    "Script",
    "Stylesheet",
    "Fetch",
    "XHR",
    "Image",
}
OPTIONAL_RESOURCE_SUFFIXES = ("/favicon.ico", ".map")
PRIVATE_MARKERS = ("gap-reference-user", "authorization", "private_key")


def classify_http_failure(url: str, resource_type: str, status: int) -> str:
    path = url.split("?", 1)[0].lower()
    if status < 400:
        return "success"
    if any(path.endswith(suffix) for suffix in OPTIONAL_RESOURCE_SUFFIXES):
        return "optional"
    if resource_type in REQUIRED_RESOURCE_TYPES:
        return "required"
    return "optional"


def classify_runtime_event(method: str, params: dict[str, Any]) -> str | None:
    if method == "Runtime.exceptionThrown":
        return "uncaught-exception"
    if method == "Runtime.consoleAPICalled":
        kind = params.get("type")
        if kind in {"error", "assert"}:
            return "console-error"
    if method == "Log.entryAdded":
        level = params.get("entry", {}).get("level")
        if level == "error":
            return "log-error"
    return None


def redact_report(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "<redacted>"
            if any(marker in key.casefold() for marker in ("path", "token", "secret"))
            else redact_report(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_report(item) for item in value]
    if isinstance(value, str):
        result = value
        for marker in PRIVATE_MARKERS:
            if marker.casefold() in result.casefold():
                result = "<redacted>"
        return result
    return value


def find_browser(explicit: str | None = None) -> Path:
    candidates = [
        explicit,
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    raise RuntimeError("Chrome or Microsoft Edge is required.")


class CDP:
    def __init__(self, websocket_url: str):
        self.websocket_url = websocket_url
        self.socket = None
        self.reader = None
        self.next_id = 1
        self.pending: dict[int, asyncio.Future] = {}
        self.events: list[dict[str, Any]] = []

    async def __aenter__(self):
        self.socket = await websockets.connect(
            self.websocket_url, open_timeout=10, max_size=8 * 1024 * 1024
        )
        self.reader = asyncio.create_task(self._read())
        return self

    async def __aexit__(self, *_):
        if self.socket:
            await self.socket.close()
        if self.reader:
            await self.reader

    async def _read(self):
        async for raw in self.socket:
            message = json.loads(raw)
            if "id" in message:
                future = self.pending.pop(message["id"], None)
                if future and not future.done():
                    future.set_result(message)
            elif "method" in message:
                self.events.append(message)

    async def command(self, method: str, params: dict | None = None) -> dict:
        identifier = self.next_id
        self.next_id += 1
        future = asyncio.get_running_loop().create_future()
        self.pending[identifier] = future
        await self.socket.send(
            json.dumps({"id": identifier, "method": method, "params": params or {}})
        )
        result = await asyncio.wait_for(future, timeout=15)
        if "error" in result:
            raise RuntimeError(f"CDP {method} failed: {result['error']['message']}")
        return result.get("result", {})

    async def evaluate(self, expression: str) -> Any:
        result = await self.command(
            "Runtime.evaluate",
            {
                "expression": expression,
                "awaitPromise": True,
                "returnByValue": True,
            },
        )
        if "exceptionDetails" in result:
            raise RuntimeError("Browser evaluation failed.")
        return result.get("result", {}).get("value")


def _json_endpoint(url: str) -> Any:
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.load(response)


def _wait_for_debug_port(profile: Path, process: subprocess.Popen) -> int:
    marker = profile / "DevToolsActivePort"
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Browser exited before DevTools became ready.")
        if marker.is_file():
            return int(marker.read_text("utf-8").splitlines()[0])
        time.sleep(0.1)
    raise TimeoutError("Timed out waiting for the browser debugging port.")


async def _wait_expression(cdp: CDP, expression: str, timeout: float = 15) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if await cdp.evaluate(expression):
            return
        await asyncio.sleep(0.1)
    raise TimeoutError(f"Browser condition timed out: {expression}")


async def _exercise(cdp: CDP, width: int, height: int) -> dict[str, Any]:
    await cdp.command("Runtime.enable")
    await cdp.command("Log.enable")
    await cdp.command("Network.enable")
    await cdp.command("Page.enable")
    await cdp.command("Page.reload", {"ignoreCache": True})
    await cdp.command(
        "Emulation.setDeviceMetricsOverride",
        {
            "width": width,
            "height": height,
            "deviceScaleFactor": 1,
            "mobile": width < 600,
        },
    )
    await _wait_expression(cdp, "document.readyState === 'complete'")
    await _wait_expression(
        cdp, "document.querySelector('#header-health')?.textContent.includes('healthy')"
    )
    version = await cdp.evaluate("document.querySelector('.version')?.textContent")
    if version != "v0.16.0":
        raise RuntimeError("Frontend version is not 0.16.0.")

    await cdp.evaluate("location.hash='create'")
    await _wait_expression(cdp, "!!document.querySelector('#generation-form')")
    controls = await cdp.evaluate(
        "!!document.querySelector('#provider-id') && !!document.querySelector('#generation-prompt')"
    )
    if not controls:
        raise RuntimeError("Create controls are unavailable.")
    await _wait_expression(
        cdp, "document.querySelectorAll('#provider-id option').length > 0"
    )
    await cdp.evaluate(
        """(() => {
          const form=document.querySelector('#generation-form');
          form.elements.provider_id.selectedIndex=0;
          form.elements.prompt.value='Instrumented Sprint 16 browser validation';
          form.requestSubmit();
          return true;
        })()"""
    )
    await _wait_expression(
        cdp,
        "document.querySelector('#create-workflow')?.dataset.workflowState === 'generated'",
    )
    await cdp.evaluate("document.querySelector('[data-action=\"verify\"]')?.click()")
    await _wait_expression(
        cdp,
        "document.querySelector('#create-workflow')?.dataset.workflowState === 'verified'",
        timeout=20,
    )
    verified = await cdp.evaluate(
        "document.querySelector('.verification-result h2')?.textContent === 'Verified'"
    )
    if not verified:
        raise RuntimeError("Final verification result was not rendered.")

    await cdp.evaluate("location.hash='developer'")
    await _wait_expression(cdp, "!!document.querySelector('#developer-content h2')")
    developer_text = await cdp.evaluate(
        "document.querySelector('#developer-content')?.textContent"
    )
    for expected in ("gapbundle", "gap media", "gap conformance"):
        if expected not in developer_text.casefold():
            raise RuntimeError(f"Developer guidance is missing {expected}.")
    await cdp.evaluate("location.hash='home'")
    await _wait_expression(cdp, "!document.querySelector('#page-home')?.hidden")
    return {
        "viewport": f"{width}x{height}",
        "version": version,
        "workflow": "verified",
        "developer_commands": True,
        "returned_home": True,
    }


async def _validate_target(websocket_url: str, width: int, height: int) -> dict:
    async with CDP(websocket_url) as cdp:
        flow = await _exercise(cdp, width, height)
        await asyncio.sleep(0.5)
        exceptions = [
            item for item in cdp.events if item["method"] == "Runtime.exceptionThrown"
        ]
        console = [
            item for item in cdp.events if item["method"] == "Runtime.consoleAPICalled"
        ]
        logs = [item for item in cdp.events if item["method"] == "Log.entryAdded"]
        failures = []
        for item in cdp.events:
            if item["method"] != "Network.responseReceived":
                continue
            response = item["params"]["response"]
            status = int(response["status"])
            if status >= 400:
                failures.append(
                    {
                        "url": response["url"],
                        "status": status,
                        "resource_type": item["params"].get("type", "Other"),
                        "classification": classify_http_failure(
                            response["url"],
                            item["params"].get("type", "Other"),
                            status,
                        ),
                    }
                )
        unhandled = [
            item for item in exceptions if "promise" in json.dumps(item).casefold()
        ]
        required = [item for item in failures if item["classification"] == "required"]
        console_errors = [
            item
            for item in console
            if classify_runtime_event(item["method"], item["params"]) == "console-error"
        ]
        log_errors = []
        for item in logs:
            if classify_runtime_event(item["method"], item["params"]) != "log-error":
                continue
            entry = item["params"].get("entry", {})
            url = entry.get("url", "")
            if url and classify_http_failure(url, "Other", 404) == "optional":
                continue
            log_errors.append(item)
        flow.update(
            {
                "uncaught_exception_count": len(exceptions),
                "unhandled_rejection_count": len(unhandled),
                "console_error_count": len(console_errors),
                "log_error_count": len(log_errors),
                "failed_required_resource_count": len(required),
                "http_failures": failures,
                "console_message_count": len(console),
            }
        )
        flow["passed"] = not (exceptions or console_errors or log_errors or required)
        return flow


def validate(url: str, browser: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="gap-browser-validation-") as directory:
        profile = Path(directory)
        process = subprocess.Popen(
            [
                str(browser),
                "--headless=new",
                "--disable-gpu",
                "--no-first-run",
                "--no-default-browser-check",
                "--remote-debugging-port=0",
                "--remote-allow-origins=*",
                f"--user-data-dir={profile}",
                url,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        try:
            port = _wait_for_debug_port(profile, process)
            browser_metadata = _json_endpoint(f"http://127.0.0.1:{port}/json/version")
            targets = _json_endpoint(f"http://127.0.0.1:{port}/json")
            target = next(item for item in targets if item["type"] == "page")
            desktop = asyncio.run(
                _validate_target(target["webSocketDebuggerUrl"], 1440, 900)
            )
            mobile = asyncio.run(
                _validate_target(target["webSocketDebuggerUrl"], 390, 844)
            )
            report = {
                "format": "gap-browser-validation-v1",
                "browser": browser.name,
                "browser_version": browser_metadata.get("Browser", "unknown"),
                "profiles": [desktop, mobile],
                "passed": desktop["passed"] and mobile["passed"],
                "temporary_profile_cleaned": True,
            }
            return redact_report(report)
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--browser")
    parser.add_argument(
        "--launch-service",
        action="store_true",
        help="Launch and clean up the repository GAP service for this run.",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    service = None
    try:
        if args.launch_service:
            service = subprocess.Popen(
                [
                    str(
                        Path(__file__).resolve().parents[1]
                        / ".venv"
                        / "Scripts"
                        / "python.exe"
                    ),
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(urllib.parse.urlsplit(args.url).port or 80),
                ],
                cwd=Path(__file__).resolve().parents[1] / "implementation",
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                if service.poll() is not None:
                    raise RuntimeError("GAP service exited before browser validation.")
                try:
                    _json_endpoint(args.url.rstrip("/") + "/health/ready")
                    break
                except Exception:
                    time.sleep(0.1)
            else:
                raise TimeoutError("Timed out waiting for the GAP service.")
        report = validate(args.url, find_browser(args.browser))
    except Exception as exc:
        report = {
            "format": "gap-browser-validation-v1",
            "passed": False,
            "error": str(exc),
        }
    finally:
        if service and service.poll() is None:
            service.terminate()
            try:
                service.wait(timeout=10)
            except subprocess.TimeoutExpired:
                service.kill()
                service.wait(timeout=5)
    print(
        json.dumps(report, sort_keys=True)
        if args.json
        else json.dumps(report, indent=2, sort_keys=True)
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
