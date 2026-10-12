from __future__ import annotations

import pytest
from conftest import STATUS, VEHICLE, VIN, sample

from mazda6e_bridge import __main__ as app
from mazda6e_bridge.api import DeviceNotVerified, MazdaAuthError, MazdaError


class FakeClient:
    def __init__(self, vehicles=None, status=None, list_error=None, status_error=None):
        self.vehicles = [VEHICLE] if vehicles is None else vehicles
        self.status = STATUS if status is None else status
        self.list_error = list_error
        self.status_error = status_error
        self.list_calls = 0

    def get_vehicles(self):
        self.list_calls += 1
        if self.list_error:
            raise self.list_error
        return self.vehicles

    def get_status(self, vehicle_id):
        if self.status_error:
            raise self.status_error
        return self.status


def test_successful_poll():
    poller = app.Poller(FakeClient())
    assert poller.poll_once(now=1000.0) == 1
    assert sample("mazda6e_scrape_success") == 1
    assert sample("mazda6e_last_success_timestamp_seconds") == 1000.0
    assert sample("mazda6e_vehicles") == 1
    assert sample("mazda6e_vehicle_scrape_success", vin=VIN) == 1
    assert sample("mazda6e_battery_soc_percent", vin=VIN) == 81


def test_network_error_marks_scrape_failed_and_retries_next_poll():
    fake = FakeClient(list_error=MazdaError("boom"))
    poller = app.Poller(fake)
    assert poller.poll_once(now=1000.0) is None
    assert sample("mazda6e_scrape_success") == 0
    assert poller.poll_once(now=1060.0) is None
    assert fake.list_calls == 2


def test_auth_error_backs_off():
    fake = FakeClient(list_error=DeviceNotVerified("verify first"))
    poller = app.Poller(fake)
    assert poller.poll_once(now=1000.0) is None
    assert poller.poll_once(now=1000.0 + app.AUTH_BACKOFF_SECONDS - 1) is None
    assert fake.list_calls == 1
    poller.poll_once(now=1000.0 + app.AUTH_BACKOFF_SECONDS)
    assert fake.list_calls == 2


def test_one_bad_vehicle_fails_the_scrape_but_keeps_running():
    poller = app.Poller(FakeClient(status_error=MazdaError("x")))
    assert poller.poll_once(now=1.0) is None
    assert sample("mazda6e_vehicle_scrape_success", vin=VIN) == 0
    assert sample("mazda6e_scrape_success") == 0


def test_config_defaults_and_validation():
    config = app.Config({"MAZDA_EMAIL": "a@b", "MAZDA_PASSWORD": "p", "MAZDA_DEVICE_ID": "d"})
    config.validate()
    assert config.poll_interval == 300
    assert config.listen_port == 9120
    assert config.export_location is False

    with pytest.raises(SystemExit, match="MAZDA_DEVICE_ID"):
        app.Config({"MAZDA_EMAIL": "a@b", "MAZDA_PASSWORD": "p"}).validate()

    with pytest.raises(SystemExit, match="60"):
        app.Config(
            {
                "MAZDA_EMAIL": "a",
                "MAZDA_PASSWORD": "p",
                "MAZDA_DEVICE_ID": "d",
                "POLL_INTERVAL_SECONDS": "10",
            }
        ).validate()


def test_export_location_parsing():
    env = {"MAZDA_EMAIL": "a", "MAZDA_PASSWORD": "p", "MAZDA_DEVICE_ID": "d"}
    assert app.Config({**env, "EXPORT_LOCATION": "true"}).export_location is True
    assert app.Config({**env, "EXPORT_LOCATION": "0"}).export_location is False


class FakeVerifyClient:
    def __init__(self, needs_code, verify_error=None):
        self.needs_code = needs_code
        self.verify_error = verify_error
        self.sent = False
        self.code = None

    def start_login(self):
        return self.needs_code

    def send_verification_email(self):
        self.sent = True

    def verify_device(self, code):
        if self.verify_error:
            raise self.verify_error
        self.code = code


def _config():
    return app.Config({"MAZDA_EMAIL": "a", "MAZDA_PASSWORD": "p", "MAZDA_DEVICE_ID": "d"})


def test_verify_device_flow(monkeypatch, capsys):
    fake = FakeVerifyClient(needs_code=True)
    monkeypatch.setattr(app, "MazdaClient", lambda *a, **k: fake)
    assert app.verify_device(_config(), read_code=lambda prompt: "123456") == 0
    assert fake.sent and fake.code == "123456"
    assert "verified" in capsys.readouterr().out


def test_verify_device_already_verified(monkeypatch):
    fake = FakeVerifyClient(needs_code=False)
    monkeypatch.setattr(app, "MazdaClient", lambda *a, **k: fake)
    assert app.verify_device(_config(), read_code=pytest.fail) == 0
    assert not fake.sent


def test_verify_device_wrong_code(monkeypatch):
    fake = FakeVerifyClient(needs_code=True, verify_error=MazdaAuthError("nope"))
    monkeypatch.setattr(app, "MazdaClient", lambda *a, **k: fake)
    assert app.verify_device(_config(), read_code=lambda prompt: "0") == 1
