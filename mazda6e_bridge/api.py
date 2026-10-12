"""Read-only client for the Mazda 6e cloud API (Europe backend).

Endpoints, headers and payload shapes are ported from
fano0001/home-assistant-mazda-6e (api.py, Apache-2.0). Only the calls that read
state are kept: login, device verification, token refresh, vehicle list and
vehicle condition. Nothing here can lock, unlock or otherwise act on a car.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import requests

from .crypto import encrypt_credential, generate_public_key

LOG = logging.getLogger("mazda6e-bridge.api")

BASE_EU = "https://cma-m.iov.changanauto.com.de/cma-app-gw"

# The backend only answers clients that look like the official iOS app.
HEADERS_BASE = {
    "content-type": "application/json",
    "devicetype": "iPhone",
    "apptype": "IOS",
    "appid": "cma",
    "accept": "*/*",
    "appversion": "V1.2.3",
    "accept-language": "en-US;q=1.0",
    "user-agent": "overseas/1.2.3 (com.mazda.mazda6e; build:1; iOS 27.0.0) Alamofire/5.5.0",
    "language": "en_US",
}

# Shown to the account owner in the "new device signed in" email.
DEVICE_NAME = "mazda6e-grafana-bridge"

# Every path this client may call. All of them read: log in, verify this
# device, renew the token, list vehicles, read their condition. _post_raw
# refuses anything else before a byte leaves the process, and CI
# (scripts/check_read_only.py) fails if this set changes or if a write route
# (car-control, security-code, serial-no, ...) appears anywhere in the package.
READ_ONLY_PATHS = frozenset(
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

TOKEN_EXPIRED = "APP_1_1_02_004"  # noqa: S105 - an error code, not a secret

# What the condition endpoint is asked to include. The flags are the ones the
# app sends; departure plans, fuel and the cool box are not on a 6e.
CONDITION_CRITERIA = {
    "seat": "1",
    "tire": "1",
    "charge": "1",
    "vehicleStatus": "1",
    "hvac": "1",
    "departurePlan": "0",
    "fuel": "0",
    "window": "1",
    "door": "1",
    "airConditionPlan": "0",
    "lamp": "1",
    "warmCoolingBox": "0",
    "welcome": "0",
    "location": "1",
}


class MazdaError(Exception):
    """A request reached Mazda and was rejected, or the reply made no sense."""


class MazdaAuthError(MazdaError):
    """Credentials were refused; retrying with the same ones will not help."""


class DeviceNotVerified(MazdaAuthError):
    """The device ID has not been confirmed with the emailed code yet."""


class ReadOnlyViolation(RuntimeError):
    """Code tried to call a path outside READ_ONLY_PATHS.

    Deliberately not a MazdaError: the poller swallows those and keeps going,
    while this one is a bug that has to stop the process.
    """


@dataclass(frozen=True)
class Vehicle:
    # Kept exactly as the backend sent it (int or str): the condition call
    # echoes it back and was only ever captured with the original type.
    vehicle_id: int | str
    vin: str
    model: str
    name: str
    series: str


def _now() -> str:
    return str(int(time.time()))


class MazdaClient:
    """Holds one session's tokens and renews them without outside help.

    An expired access token is refreshed; a refused refresh falls back to a
    fresh password login with the same device ID, which a verified device passes
    without a new email code.
    """

    def __init__(
        self,
        email: str,
        password: str,
        device_id: str,
        *,
        base_url: str = BASE_EU,
        timeout: float = 30.0,
        session: requests.Session | None = None,
    ) -> None:
        self._email = email
        self._password = password
        self.device_id = device_id
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()
        self.token: str | None = None
        self.refresh: str | None = None

    # -- transport ---------------------------------------------------------

    def _post_raw(self, path: str, body: dict, headers: dict) -> dict:
        if path not in READ_ONLY_PATHS:
            raise ReadOnlyViolation(f"refusing to call {path}: not a read-only endpoint")
        try:
            resp = self.session.post(
                f"{self.base_url}{path}", json=body, headers=headers, timeout=self.timeout
            )
        except requests.RequestException as exc:
            raise MazdaError(f"request to {path} failed: {exc.__class__.__name__}") from None
        if resp.status_code != 200:
            raise MazdaError(f"{path} answered HTTP {resp.status_code}")
        try:
            data = resp.json()
        except ValueError:
            raise MazdaError(f"{path} returned a body that is not JSON") from None
        if not isinstance(data, dict):
            raise MazdaError(f"{path} returned an unexpected JSON type")
        return data

    def _headers(self) -> dict:
        return {**HEADERS_BASE, "authorization": self.token or "", "deviceid": self.device_id}

    def _call(self, path: str, body: dict) -> dict:
        """POST with the access token, renewing it once if the backend says it expired."""
        if self.token is None:
            self.login()
        data = self._post_raw(path, body, self._headers())
        if data.get("success") is True:
            return data
        if data.get("code") == TOKEN_EXPIRED:
            LOG.info("access token expired, renewing")
            self._renew()
            data = self._post_raw(path, body, self._headers())
            if data.get("success") is True:
                return data
        raise MazdaError(f"{path} rejected ({data.get('code', 'unknown')}: {data.get('msg', '')})")

    # -- authentication ----------------------------------------------------

    def login(self) -> None:
        """Password login. Raises DeviceNotVerified when the email code is still owed."""
        needs_verification = self.start_login()
        if needs_verification:
            raise DeviceNotVerified(
                "this MAZDA_DEVICE_ID is not verified yet: run `mazda6e-bridge verify-device` once"
            )

    def start_login(self) -> bool:
        """Log in and return whether the backend wants the emailed code first."""
        body = {
            "loginTime": _now(),
            "email": encrypt_credential(self._email),
            "password": encrypt_credential(self._password),
            "pubKey": generate_public_key(),
        }
        headers = {**HEADERS_BASE, "deviceid": self.device_id}
        data = self._post_raw("/cma-app-auth/api/login/email-pass-in/v2", body, headers)
        if not data.get("success"):
            raise MazdaAuthError(f"login refused (code {data.get('code', 'unknown')})")
        payload = data.get("data") or {}
        token, refresh = payload.get("token"), payload.get("refreshToken")
        if not (isinstance(token, str) and token and isinstance(refresh, str) and refresh):
            raise MazdaError("login reply carried no token pair")
        self.token, self.refresh = token, refresh
        return payload.get("emailVerify") is True

    def send_verification_email(self) -> None:
        self._post_checked(
            "/cma-app-user/api/send-email/device-login/send",
            {
                "email": encrypt_credential(self._email),
                "deviceName": DEVICE_NAME,
                "loginTime": _now(),
                "type": "1",
            },
        )

    def verify_device(self, code: str) -> None:
        data = self._post_checked(
            "/cma-app-user/api/login-device/email-verify",
            {
                "authCode": code.strip(),
                "email": encrypt_credential(self._email),
                "deviceName": DEVICE_NAME,
                "lastLoginTime": _now(),
                "type": "3",
                "deviceModel": DEVICE_NAME,
            },
        )
        if data.get("data") is not True:
            raise MazdaAuthError("the verification code was not accepted")

    def _post_checked(self, path: str, body: dict) -> dict:
        data = self._post_raw(path, body, self._headers())
        if data.get("success") is not True:
            raise MazdaAuthError(f"{path} rejected (code {data.get('code', 'unknown')})")
        return data

    def refresh_token(self) -> None:
        headers = {**HEADERS_BASE, "authorization": self.token or ""}
        data = self._post_raw(
            "/cma-app-auth/api/auth/refresh-token", {"refreshToken": self.refresh}, headers
        )
        payload = data.get("data") or {}
        if not data.get("success") or not payload.get("token"):
            raise MazdaAuthError("token refresh refused")
        self.token, self.refresh = payload["token"], payload.get("refreshToken", self.refresh)

    def _renew(self) -> None:
        try:
            self.refresh_token()
        except MazdaError as exc:
            LOG.info("token refresh failed (%s), logging in again", exc)
            self.login()

    # -- reads -------------------------------------------------------------

    def get_vehicles(self) -> list[Vehicle]:
        data = self._call("/cma-app-user/api/vehicle/vehicles", {})
        # Some accounts get an empty list from the legacy route although the
        # app shows their car; the newer route lists it.
        if not data.get("data"):
            data = self._call("/cma-app-user/api/car/vehicles", {})
        vehicles = []
        for raw in data.get("data") or []:
            vehicle_id = raw.get("carId") or raw.get("vehicleId")
            vin = raw.get("vin")
            if vehicle_id is None or not vin:
                continue
            model = raw.get("modelName") or "Mazda 6e"
            vehicles.append(
                Vehicle(
                    vehicle_id=vehicle_id,
                    vin=vin,
                    model=model,
                    name=raw.get("carName") or model,
                    series=raw.get("seriesName") or "",
                )
            )
        return vehicles

    def get_status(self, vehicle_id: int | str) -> dict:
        data = self._call(
            "/cma-app-car-condition/api/vehicle/condition/v2",
            {"vechileCriteria": CONDITION_CRITERIA, "vehicleId": vehicle_id},
        )
        status = data.get("data")
        if not isinstance(status, dict):
            raise MazdaError("vehicle condition reply carried no data")
        return status
