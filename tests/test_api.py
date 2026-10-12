from __future__ import annotations

import base64
import json

import pytest
import responses
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from mazda6e_bridge import crypto
from mazda6e_bridge.api import (
    BASE_EU,
    DeviceNotVerified,
    MazdaAuthError,
    MazdaClient,
    MazdaError,
)

LOGIN = f"{BASE_EU}/cma-app-auth/api/login/email-pass-in/v2"
REFRESH = f"{BASE_EU}/cma-app-auth/api/auth/refresh-token"
VEHICLES = f"{BASE_EU}/cma-app-user/api/vehicle/vehicles"
CAR_VEHICLES = f"{BASE_EU}/cma-app-user/api/car/vehicles"
CONDITION = f"{BASE_EU}/cma-app-car-condition/api/vehicle/condition/v2"
SEND_CODE = f"{BASE_EU}/cma-app-user/api/send-email/device-login/send"
VERIFY = f"{BASE_EU}/cma-app-user/api/login-device/email-verify"


def login_ok(token="t1", refresh="r1", verify=False):
    return {
        "success": True,
        "data": {"token": token, "refreshToken": refresh, "emailVerify": verify},
    }


def client():
    return MazdaClient("me@example.com", "hunter2", "11111111-2222-3333-4444-555555555555")


@responses.activate
def test_login_sends_encrypted_credentials_and_device_id():
    responses.post(LOGIN, json=login_ok())
    c = client()
    c.login()

    assert c.token == "t1"
    request = responses.calls[0].request
    body = json.loads(request.body)
    assert request.headers["deviceid"] == c.device_id
    assert "hunter2" not in request.body.decode()
    assert "me@example.com" not in request.body.decode()
    assert set(body) == {"loginTime", "email", "password", "pubKey"}


@responses.activate
def test_unverified_device_raises():
    responses.post(LOGIN, json=login_ok(verify=True))
    with pytest.raises(DeviceNotVerified):
        client().login()


@responses.activate
def test_refused_login_is_an_auth_error():
    responses.post(LOGIN, json={"success": False, "code": "APP_1_1_01_001"})
    with pytest.raises(MazdaAuthError, match="APP_1_1_01_001"):
        client().login()


@responses.activate
def test_first_call_logs_in_and_lists_vehicles():
    responses.post(LOGIN, json=login_ok())
    responses.post(
        VEHICLES,
        json={
            "success": True,
            "data": [{"carId": 4711, "vin": "VIN1", "modelName": "Mazda 6e", "carName": None}],
        },
    )
    vehicles = client().get_vehicles()

    assert len(vehicles) == 1
    assert vehicles[0].vehicle_id == 4711
    assert vehicles[0].name == "Mazda 6e"
    assert responses.calls[1].request.headers["authorization"] == "t1"


@responses.activate
def test_empty_legacy_list_falls_back_to_car_route():
    responses.post(LOGIN, json=login_ok())
    responses.post(VEHICLES, json={"success": True, "data": []})
    responses.post(
        CAR_VEHICLES,
        json={"success": True, "data": [{"vehicleId": "9", "vin": "VIN9", "modelName": "6e"}]},
    )
    assert [v.vin for v in client().get_vehicles()] == ["VIN9"]


@responses.activate
def test_expired_token_is_refreshed_once():
    responses.post(LOGIN, json=login_ok())
    responses.post(CONDITION, json={"success": False, "code": "APP_1_1_02_004"})
    responses.post(REFRESH, json={"success": True, "data": {"token": "t2", "refreshToken": "r2"}})
    responses.post(CONDITION, json={"success": True, "data": {"vehicleStatus": {"soc": 50}}})

    c = client()
    assert c.get_status(4711) == {"vehicleStatus": {"soc": 50}}
    assert c.token == "t2"
    assert c.refresh == "r2"
    assert responses.calls[-1].request.headers["authorization"] == "t2"
    assert json.loads(responses.calls[-1].request.body)["vehicleId"] == 4711


@responses.activate
def test_refused_refresh_falls_back_to_password_login():
    responses.post(LOGIN, json=login_ok())
    responses.post(CONDITION, json={"success": False, "code": "APP_1_1_02_004"})
    responses.post(REFRESH, json={"success": False, "code": "nope"})
    responses.post(LOGIN, json=login_ok(token="t3", refresh="r3"))
    responses.post(CONDITION, json={"success": True, "data": {}})

    c = client()
    assert c.get_status(1) == {}
    assert c.token == "t3"


@responses.activate
def test_other_rejections_raise_without_secrets():
    responses.post(LOGIN, json=login_ok())
    responses.post(CONDITION, json={"success": False, "code": "X", "msg": "bad vehicle"})
    with pytest.raises(MazdaError, match="X: bad vehicle"):
        client().get_status(1)


@responses.activate
def test_http_errors_and_garbage_raise_mazda_error():
    responses.post(LOGIN, status=502)
    with pytest.raises(MazdaError, match="HTTP 502"):
        client().login()

    responses.replace(responses.POST, LOGIN, body="<html>")
    with pytest.raises(MazdaError, match="not JSON"):
        client().login()


@responses.activate
def test_device_verification_flow():
    responses.post(LOGIN, json=login_ok(verify=True))
    responses.post(SEND_CODE, json={"success": True, "data": True})
    responses.post(VERIFY, json={"success": True, "data": True})

    c = client()
    assert c.start_login() is True
    c.send_verification_email()
    c.verify_device(" 123456 ")
    assert json.loads(responses.calls[-1].request.body)["authCode"] == "123456"


@responses.activate
def test_wrong_verification_code():
    responses.post(LOGIN, json=login_ok(verify=True))
    responses.post(VERIFY, json={"success": True, "data": False})
    c = client()
    c.start_login()
    with pytest.raises(MazdaAuthError):
        c.verify_device("000000")


def test_encrypt_credential_round_trips():
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = base64.b64encode(
        private.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        )
    ).decode()
    secret = "ü" * 200  # 400 bytes: forces two RSA blocks
    blob = base64.b64decode(crypto.encrypt_credential(secret, public))
    plain = b"".join(
        private.decrypt(blob[i : i + 256], padding.PKCS1v15()) for i in range(0, len(blob), 256)
    )
    assert plain.decode() == secret


def test_encrypt_rejects_bad_key():
    with pytest.raises(crypto.CryptoError):
        crypto.encrypt_credential("x", "not-a-key")


def test_generated_public_key_is_2048_bit_rsa():
    der = base64.b64decode(crypto.generate_public_key())
    key = serialization.load_der_public_key(der)
    assert isinstance(key, rsa.RSAPublicKey)
    assert key.key_size == 2048


def test_server_key_loads():
    assert crypto.encrypt_credential("x")
