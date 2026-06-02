from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import create_app
PAGE_PATHS = ["/", "/bookings", "/visualization", "/prediction"]
API_GET_PATHS = [
    "/health",
    "/api/dashboard/summary",
    "/api/dashboard/trend?granularity=month",
    "/api/bookings/filter-options",
    "/api/bookings?page=1&page_size=5",
    "/api/visualization/overview",
    "/api/prediction/candidate-bookings?page=1&page_size=5",
    "/api/prediction/model-metrics",
    "/api/prediction/batch-records",
    "/api/realtime/summary",
    "/api/realtime/trend",
    "/api/realtime/recent-predictions",
]
API_POSTS = [
    ("/api/prediction/single", {"booking_id": 1}),
]


def fetch_calls() -> set[str]:
    calls: set[str] = set()
    for js_file in (ROOT / "app" / "static" / "js").glob("*.js"):
        text = js_file.read_text(encoding="utf-8")
        calls.update(re.findall(r'fetch\(`?([^`"\']+)', text))
    return calls


def main() -> int:
    base_url = os.environ.get("INTEGRATION_BASE_URL")
    if base_url:
        return check_live_http(base_url.rstrip("/"))

    app = create_app({"TESTING": True})
    client = app.test_client()
    failures: list[str] = []

    for path in PAGE_PATHS:
        response = client.get(path)
        print(f"PAGE {path}: {response.status_code} {response.content_type} {len(response.data)} bytes")
        if response.status_code != 200:
            failures.append(f"{path} returned {response.status_code}")

    for path in API_GET_PATHS:
        response = client.get(path)
        print(f"GET  {path}: {response.status_code} {response.content_type} {len(response.data)} bytes")
        if response.status_code != 200:
            failures.append(f"{path} returned {response.status_code}")
            continue
        if path != "/health":
            payload = response.get_json()
            if not payload or payload.get("success") is not True or "data" not in payload:
                failures.append(f"{path} does not match API envelope")

    for path, body in API_POSTS:
        response = client.post(path, data=json.dumps(body), content_type="application/json")
        print(f"POST {path}: {response.status_code} {response.content_type} {len(response.data)} bytes")
        if response.status_code != 200:
            failures.append(f"{path} returned {response.status_code}")

    registered = {str(rule) for rule in app.url_map.iter_rules()}
    for call in sorted(fetch_calls()):
        static_prefix = call.split("${", 1)[0].split("?", 1)[0]
        if static_prefix.startswith("/api/") and static_prefix not in registered:
            failures.append(f"front-end fetch path is not registered: {call}")

    if failures:
        print("\nFAILURES")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("\nIntegration smoke check passed.")
    return 0


def check_live_http(base_url: str) -> int:
    failures: list[str] = []
    for path in PAGE_PATHS + API_GET_PATHS:
        url = f"{base_url}{path}"
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                body = response.read()
                status = response.status
                content_type = response.headers.get("content-type", "")
        except urllib.error.HTTPError as error:
            status = error.code
            body = error.read()
            content_type = error.headers.get("content-type", "")
        print(f"HTTP GET  {path}: {status} {content_type} {len(body)} bytes")
        if status != 200:
            failures.append(f"{path} returned {status}")
            continue
        if path.startswith("/api/"):
            payload = json.loads(body.decode("utf-8"))
            if payload.get("success") is not True or "data" not in payload:
                failures.append(f"{path} does not match API envelope")

    for path, payload in API_POSTS:
        request = urllib.request.Request(
            f"{base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read()
            print(f"HTTP POST {path}: {response.status} {response.headers.get('content-type', '')} {len(body)} bytes")
            if response.status != 200:
                failures.append(f"{path} returned {response.status}")

    if failures:
        print("\nFAILURES")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("\nLive HTTP integration check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
