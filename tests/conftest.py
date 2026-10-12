from __future__ import annotations

import copy

import pytest
from prometheus_client import REGISTRY

from mazda6e_bridge import metrics
from mazda6e_bridge.api import Vehicle

VIN = "LVTEST00000000001"

VEHICLE = Vehicle(vehicle_id=4711, vin=VIN, model="Mazda 6e", name="Shark", series="Takumi")

# Shaped like a captured /vehicle/condition/v2 reply (Europe). Values are made up.
STATUS = {
    "lastUpdatedAt": 1760000000000,
    "vehicleStatus": {
        "soc": 81,
        "drvMileage": 402,
        "totalMileage": 12345,
        "speed": 0,
        "powerStatus": 0,
        "status": 2,
        "connectStatus": 1,
        "steeringWheelHeater": 0,
    },
    "charge": {
        "maxSocPercent": 90,
        "chargeCurrent": 15.5,
        "acChargeCurrent": 15.5,
        "dcChargeCurrent": 0,
        "remainChargeTime": 45,
        "chargeStatus": 6,
        "chargeConStatus": 1,
        "dcChargeGunConnectStatus": 0,
    },
    "door": {"doors": [0, 1, 0, 0], "trunk": 0, "driverLock": 2, "passengerLock": 2},
    "window": {"windows": [0, 0, 1, 0], "openDegree": [0, 0, 30, 0]},
    "lamp": {"lowBeam": 0, "highBeam": 0, "positionLamp": 1, "leftTurn": 0, "rightTurn": 0},
    "tire": {
        "leftFront": {"pressure": 250, "status": 0},
        "rightFront": {"pressure": 251, "status": 0},
        "leftBack": {"pressure": 260, "status": 0},
        "rightBack": {"pressure": 259, "status": 0},
    },
    "seat": {
        "leftFront": {"mode": 1, "level": 2},
        "rightFront": {"mode": 0, "level": 0},
    },
    "hvac": {
        "insideTemp": 215,
        "consTempCockpit": 0,
        "remoteTemp": 220,
        "insideHumidity": 48,
        "insidePm25": 7,
        "acStatus": 1,
        "defrostStatus": 0,
    },
    "location": {"latitude": "52.0907", "longitude": "5.1214"},
}


@pytest.fixture
def status():
    return copy.deepcopy(STATUS)


@pytest.fixture(autouse=True)
def _reset_metrics():
    """Gauges are module globals; start every test from an empty registry state."""
    for value in vars(metrics).values():
        if hasattr(value, "_metrics"):
            value.clear()
    for gauge in (metrics.SCRAPE_SUCCESS, metrics.LAST_SUCCESS, metrics.VEHICLES):
        gauge.set(0)
    yield


def sample(metric: str, **labels) -> float | None:
    return REGISTRY.get_sample_value(metric, labels)
