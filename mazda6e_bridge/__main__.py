"""Entry point: `serve` (default) runs the exporter; `verify-device` confirms the device once."""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time

from prometheus_client import start_http_server

from . import metrics
from .api import BASE_EU, DeviceNotVerified, MazdaAuthError, MazdaClient, MazdaError

LOG = logging.getLogger("mazda6e-bridge")

# After a refused login, wait this long before trying the password again, so a
# wrong password or an unverified device cannot hammer the account into a lockout.
AUTH_BACKOFF_SECONDS = 3600


def _bool(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "yes", "on")


class Config:
    """Runtime configuration, sourced entirely from environment variables."""

    def __init__(self, env: dict[str, str] | None = None) -> None:
        env = os.environ if env is None else env
        self.email = env.get("MAZDA_EMAIL", "").strip()
        self.password = env.get("MAZDA_PASSWORD", "")
        self.device_id = env.get("MAZDA_DEVICE_ID", "").strip()
        self.base_url = env.get("MAZDA_API_BASE_URL", BASE_EU).strip() or BASE_EU
        self.poll_interval = int(env.get("POLL_INTERVAL_SECONDS", "300"))
        self.listen_port = int(env.get("LISTEN_PORT", "9120"))
        self.export_location = _bool(env.get("EXPORT_LOCATION", "false"))
        self.timeout = float(env.get("REQUEST_TIMEOUT_SECONDS", "30"))

    def validate(self) -> None:
        missing = [
            name
            for name, value in (
                ("MAZDA_EMAIL", self.email),
                ("MAZDA_PASSWORD", self.password),
                ("MAZDA_DEVICE_ID", self.device_id),
            )
            if not value
        ]
        if missing:
            raise SystemExit(
                f"missing required environment variable(s): {', '.join(missing)}"
                + (
                    "\nMAZDA_DEVICE_ID can be any UUID you keep, e.g. the output of "
                    "`python -c 'import uuid; print(uuid.uuid4())'`"
                    if "MAZDA_DEVICE_ID" in missing
                    else ""
                )
            )
        if self.poll_interval < 60:
            raise SystemExit("POLL_INTERVAL_SECONDS below 60 is not allowed: be kind to the API")


class Poller:
    def __init__(self, client: MazdaClient, export_location: bool = False) -> None:
        self.client = client
        self.export_location = export_location
        self.auth_blocked_until = 0.0

    def poll_once(self, now: float | None = None) -> int | None:
        """Poll every vehicle once. Returns how many were read, or None on failure.

        Never raises: errors become scrape_success=0 and a log line.
        """
        now = time.time() if now is None else now
        if now < self.auth_blocked_until:
            LOG.warning("skipping poll: login refused earlier, retrying after backoff")
            metrics.SCRAPE_SUCCESS.set(0)
            return None
        try:
            vehicles = self.client.get_vehicles()
        except MazdaAuthError as exc:
            self.auth_blocked_until = now + AUTH_BACKOFF_SECONDS
            metrics.SCRAPE_SUCCESS.set(0)
            LOG.error("%s (next attempt in %ds)", exc, AUTH_BACKOFF_SECONDS)
            return None
        except MazdaError as exc:
            metrics.SCRAPE_SUCCESS.set(0)
            LOG.error("failed to list vehicles: %s", exc)
            return None

        metrics.VEHICLES.set(len(vehicles))
        read = 0
        for vehicle in vehicles:
            try:
                status = self.client.get_status(vehicle.vehicle_id)
                metrics.update_vehicle(vehicle, status, export_location=self.export_location)
            except Exception as exc:  # noqa: BLE001 - one bad reply must not stop the others
                metrics.VEHICLE_SCRAPE_SUCCESS.labels(vehicle.vin).set(0)
                LOG.error("failed to read vehicle %s: %s", vehicle.vin[-6:], exc)
                continue
            metrics.VEHICLE_SCRAPE_SUCCESS.labels(vehicle.vin).set(1)
            read += 1

        ok = read == len(vehicles)
        metrics.SCRAPE_SUCCESS.set(1 if ok else 0)
        if ok:
            metrics.LAST_SUCCESS.set(now)
        LOG.info("polled %d of %d vehicle(s)", read, len(vehicles))
        return read if ok else None


def serve(config: Config) -> None:  # pragma: no cover - process wiring
    metrics.SCRAPE_SUCCESS.set(0)
    start_http_server(config.listen_port)
    LOG.info(
        "serving metrics on :%d, polling every %ds (location %s)",
        config.listen_port,
        config.poll_interval,
        "exported" if config.export_location else "not exported",
    )
    client = MazdaClient(
        config.email,
        config.password,
        config.device_id,
        base_url=config.base_url,
        timeout=config.timeout,
    )
    poller = Poller(client, export_location=config.export_location)
    while True:
        poller.poll_once()
        time.sleep(config.poll_interval)


def verify_device(config: Config, read_code=input) -> int:
    """Log in once interactively and confirm MAZDA_DEVICE_ID with the emailed code."""
    client = MazdaClient(
        config.email,
        config.password,
        config.device_id,
        base_url=config.base_url,
        timeout=config.timeout,
    )
    try:
        if not client.start_login():
            print("This device ID is already verified; the exporter can log in on its own.")
            return 0
        client.send_verification_email()
        code = read_code("Mazda emailed a verification code. Enter it: ")
        client.verify_device(code)
    except MazdaError as exc:
        print(f"verification failed: {exc}", file=sys.stderr)
        return 1
    print("Device verified. Keep MAZDA_DEVICE_ID unchanged from now on.")
    return 0


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - process wiring
    parser = argparse.ArgumentParser(
        prog="mazda6e-bridge", description="Prometheus exporter for the Mazda 6e cloud API."
    )
    parser.add_argument("command", nargs="?", default="serve", choices=("serve", "verify-device"))
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
    )
    config = Config()
    config.validate()
    if args.command == "verify-device":
        return verify_device(config)
    try:
        serve(config)
    except DeviceNotVerified as exc:
        LOG.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
