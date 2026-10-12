"""The bridge must not be able to act on the car; these keep that true."""

from __future__ import annotations

import pytest
import responses

from mazda6e_bridge.api import BASE_EU, READ_ONLY_PATHS, MazdaClient, ReadOnlyViolation
from scripts.check_read_only import EXPECTED_PATHS, check_package, check_source


def test_package_passes_the_guard():
    assert check_package() == []


def test_allowlist_is_pinned():
    assert READ_ONLY_PATHS == EXPECTED_PATHS


@responses.activate
def test_client_refuses_unlisted_path_before_sending():
    client = MazdaClient("a@b", "p", "d")
    with pytest.raises(ReadOnlyViolation):
        client._post_raw("/cma-app-car-control/api/control/doors", {"open": True}, {})
    assert len(responses.calls) == 0


def test_violation_is_not_swallowed_as_a_mazda_error():
    from mazda6e_bridge.api import MazdaError

    assert not issubclass(ReadOnlyViolation, MazdaError)


@pytest.mark.parametrize(
    "source",
    [
        'URL = "/cma-app-car-control/api/control/doors"',
        'URL = "/cma-app-user/api/some/new/route"',
        'payload = {"safeCode": pin}',
        "def sign_control_payload(p): ...",
        "key.sign(data, padding, algo)",
        "key.decrypt(blob, padding)",
        "der = key.private_bytes(enc, fmt, alg)",
        "control_pin = env['PIN']",
    ],
)
def test_guard_catches_write_side_code(source):
    assert check_source(source, "probe.py")


def test_guard_ignores_comments():
    assert check_source("# never call car-control or security-code\nx = 1\n", "probe.py") == []


def test_guard_counts_http_call_sites():
    source = "self.session.post(u)\nself.session.get(u)\n"
    assert check_source(source, "probe.py") == ["probe.py: __http_calls__=2"]


def test_base_url_is_not_part_of_the_allowlist_check():
    # The host is configurable for tests; the path is what decides read or write.
    assert not BASE_EU.endswith("/api")
