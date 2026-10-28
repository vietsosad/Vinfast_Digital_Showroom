"""Black-box smoke test for a running backend (container or local process).

    python backend/scripts/smoke_test.py --base-url http://127.0.0.1:8000 --write-state state.json
    # restart the container, then:
    python backend/scripts/smoke_test.py --base-url http://127.0.0.1:8000 --check-state state.json

Uses only the standard library so it can run anywhere, including CI runners.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path


class SmokeTestError(AssertionError):
    pass


def request(base_url: str, method: str, path: str, body: dict | None = None, token: str | None = None):
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{base_url}{path}", data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            raw = response.read()
            return response.status, (json.loads(raw) if raw and "json" in response.headers.get("Content-Type", "") else raw)
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            return exc.code, json.loads(raw)
        except ValueError:
            return exc.code, raw


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeTestError(message)
    print(f"  ok  {message}")


def wait_until_healthy(base_url: str, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        try:
            last = request(base_url, "GET", "/health")
            if last[0] == 200 and last[1].get("database") == "connected":
                print(f"  ok  /health -> {last[1]}")
                return
        except OSError as exc:
            last = exc
        time.sleep(1)
    raise SmokeTestError(f"service not healthy within {timeout}s (last: {last})")


def login(base_url: str, email: str, password: str) -> str:
    status, body = request(base_url, "POST", "/api/v1/auth/login", {"email": email, "password": password})
    expect(status == 200 and "access_token" in body, f"login {email} -> {status}")
    return body["access_token"]


def run(args: argparse.Namespace) -> None:
    base = args.base_url.rstrip("/")
    wait_until_healthy(base, args.timeout)

    status, _ = request(base, "GET", "/docs")
    expect(status == 200, "Swagger UI /docs is served")
    status, spec = request(base, "GET", "/openapi.json")
    expect(status == 200 and "/api/v1/bookings" in spec["paths"], "OpenAPI document lists the API")

    status, cars = request(base, "GET", "/api/v1/cars")
    expect(status == 200 and len(cars) > 0, f"catalog is seeded ({len(cars)} cars)")
    status, locations = request(base, "GET", "/api/v1/locations")
    expect(status == 200 and locations["total"] > 0, f"locations are seeded ({locations['total']})")

    for method, path in (("GET", "/api/v1/bookings"), ("POST", "/api/v1/bookings"), ("GET", "/api/v1/auth/me")):
        status, _ = request(base, method, path, {} if method == "POST" else None)
        expect(status == 401, f"{method} {path} without token -> 401")

    token = login(base, args.email, args.password)
    status, me = request(base, "GET", "/api/v1/auth/me", token=token)
    expect(status == 200 and me["email"] == args.email, "GET /auth/me with token -> 200")

    if args.write_state:
        car = next(item for item in cars if item["is_active"])
        payload = {"vehicle_id": car["id"], "preferred_date": str(date.today() + timedelta(days=3)), "notes": "smoke"}
        status, booking = request(base, "POST", "/api/v1/bookings", payload, token=token)
        expect(status == 201 and booking["user_id"] == me["id"], "POST /bookings with token -> 201, owned by caller")
        Path(args.write_state).write_text(json.dumps({"booking_id": booking["id"]}), encoding="utf-8")

    if args.check_state:
        booking_id = json.loads(Path(args.check_state).read_text(encoding="utf-8"))["booking_id"]
        status, bookings = request(base, "GET", "/api/v1/bookings", token=token)
        expect(status == 200 and any(item["id"] == booking_id for item in bookings), "booking persisted across restart")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--email", default="customer@gmail.com")
    parser.add_argument("--password", default="123456")
    parser.add_argument("--write-state", help="Create a booking and store its id in this file")
    parser.add_argument("--check-state", help="Verify the booking stored by --write-state still exists")
    args = parser.parse_args()
    try:
        run(args)
    except SmokeTestError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    print("Smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
