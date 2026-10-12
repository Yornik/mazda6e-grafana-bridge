#!/usr/bin/env python3
"""Fail if the shipped package could do anything but read.

The bridge holds credentials that can drive the car, so "read-only" is checked
rather than promised. Over every module in mazda6e_bridge/ this asserts:

1. The endpoint allowlist (api.READ_ONLY_PATHS) is exactly the set pinned
   below. Adding a path means changing both files, which a reviewer sees.
2. Every API-path-looking string in the code is on that list.
3. No string or name mentions a vehicle-control route or field
   (car-control, security-code, serial-no, rcToken, ...).
4. Nothing can sign a command: no .sign() or .decrypt() call, and no private
   key is ever serialized, so the key registered at login dies with the process.
5. One HTTP choke point: the session is used in exactly one place
   (MazdaClient._post_raw, which enforces the allowlist at runtime as well).

Only syntax is inspected (strings, names, attributes), never comments, so the
comments explaining what is forbidden do not trip the check.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent / "mazda6e_bridge"

# The pinned copy. Keep it in step with READ_ONLY_PATHS in mazda6e_bridge/api.py,
# and only ever with endpoints that read.
EXPECTED_PATHS = frozenset(
    {
        "/cma-app-auth/api/login/email-pass-in/v2",
        "/cma-app-auth/api/auth/refresh-token",
        "/cma-app-user/api/send-email/device-login/send",
        "/cma-app-user/api/login-device/email-verify",
        "/cma-app-user/api/vehicle/vehicles",
        "/cma-app-user/api/car/vehicles",
        "/cma-app-car-condition/api/vehicle/condition/v2",
    }
)

# Fragments of the write side of the API, taken from the Home Assistant
# integration this was ported from. Matched case-insensitively.
FORBIDDEN_FRAGMENTS = (
    "car-control",
    "/control/",
    "control-result",
    "security-code",
    "serial-no",
    "heating-plans",
    "charge/percentage",
    "safecode",
    "rctoken",
    "seriralno",
    "control_pin",
    "control_private_key",
    "sign_control",
    "decrypt_control",
)

# Calls that would sign a command or recover a control serial, or keep the
# private half of the login key.
FORBIDDEN_ATTRIBUTES = frozenset({"sign", "decrypt", "private_bytes"})

HTTP_METHODS = frozenset({"get", "post", "put", "patch", "delete", "request", "head"})


def _looks_like_path(text: str) -> bool:
    return text.startswith("/") and "/api/" in text


def check_source(source: str, filename: str) -> list[str]:
    """Problems found in one module's source."""
    problems = []
    tree = ast.parse(source, filename)
    http_calls = 0
    for node in ast.walk(tree):
        texts: list[str] = []
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            texts.append(node.value)
            if _looks_like_path(node.value) and node.value not in EXPECTED_PATHS:
                problems.append(f"{filename}:{node.lineno}: API path not allowlisted: {node.value}")
        elif isinstance(node, ast.Name):
            texts.append(node.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            texts.append(node.name)
        elif isinstance(node, ast.Attribute):
            texts.append(node.attr)
            if node.attr in FORBIDDEN_ATTRIBUTES:
                problems.append(f"{filename}:{node.lineno}: forbidden call .{node.attr}()")
            if (
                node.attr in HTTP_METHODS
                and isinstance(node.value, ast.Attribute)
                and node.value.attr == "session"
            ):
                http_calls += 1
        for text in texts:
            lowered = text.lower()
            for fragment in FORBIDDEN_FRAGMENTS:
                if fragment in lowered:
                    problems.append(
                        f"{filename}:{getattr(node, 'lineno', '?')}: "
                        f"write-side reference {fragment!r} in {text[:60]!r}"
                    )
    if http_calls:
        problems.append(f"{filename}: __http_calls__={http_calls}")
    return problems


def check_package(package: Path = PACKAGE) -> list[str]:
    problems: list[str] = []
    http_calls = 0
    for path in sorted(package.rglob("*.py")):
        for problem in check_source(path.read_text(encoding="utf-8"), str(path.name)):
            if "__http_calls__=" in problem:
                http_calls += int(problem.rsplit("=", 1)[1])
            else:
                problems.append(problem)
    if http_calls != 1:
        problems.append(
            f"expected exactly one HTTP call site (MazdaClient._post_raw), found {http_calls}"
        )

    sys.path.insert(0, str(package.parent))
    from mazda6e_bridge.api import READ_ONLY_PATHS

    if READ_ONLY_PATHS != EXPECTED_PATHS:
        added = sorted(READ_ONLY_PATHS - EXPECTED_PATHS)
        removed = sorted(EXPECTED_PATHS - READ_ONLY_PATHS)
        problems.append(f"READ_ONLY_PATHS changed: added {added}, removed {removed}")
    return problems


def main() -> int:
    problems = check_package()
    for problem in problems:
        print(f"::error::{problem}")
    if problems:
        print(f"read-only guard: {len(problems)} problem(s)")
        return 1
    print(f"read-only guard: OK ({len(EXPECTED_PATHS)} allowlisted read endpoints)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
