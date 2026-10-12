"""Map a Mazda 6e vehicle-condition reply onto Prometheus gauges.

Field names and their meaning come from the sensor definitions in
fano0001/home-assistant-mazda-6e. Every reading is optional: a field the car
does not report removes its series instead of publishing a misleading 0.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from prometheus_client import Gauge

from .api import Vehicle

_V = ("vin",)

VEHICLE_INFO = Gauge(
    "mazda6e_vehicle_info",
    "Always 1; carries the vehicle's descriptive labels.",
    ("vin", "model", "name", "series"),
)
VEHICLE_SCRAPE_SUCCESS = Gauge(
    "mazda6e_vehicle_scrape_success",
    "1 if this vehicle's condition was read on the most recent poll, 0 otherwise.",
    _V,
)
STATUS_UPDATED = Gauge(
    "mazda6e_status_updated_timestamp_seconds",
    "Unix time the car last reported its condition to the Mazda cloud.",
    _V,
)
ONLINE = Gauge("mazda6e_online", "1 if the car is connected to the Mazda cloud.", _V)

# --- battery, range, driving ---
SOC = Gauge("mazda6e_battery_soc_percent", "High-voltage battery state of charge in %.", _V)
RANGE = Gauge("mazda6e_range_km", "Remaining driving range in km.", _V)
ODOMETER = Gauge("mazda6e_odometer_km", "Odometer reading in km.", _V)
SPEED = Gauge("mazda6e_speed_kmh", "Vehicle speed in km/h.", _V)
POWER_STATE = Gauge(
    "mazda6e_power_state",
    "1 for the current power state (off/accessory/on/unknown), else 0.",
    ("vin", "state"),
)
VEHICLE_STATE = Gauge(
    "mazda6e_vehicle_state",
    "1 for the current driving state (driving/parked/unknown), else 0.",
    ("vin", "state"),
)

# --- charging ---
CHARGE_TARGET = Gauge("mazda6e_charge_target_soc_percent", "Charge limit in %.", _V)
CHARGE_CURRENT = Gauge(
    "mazda6e_charge_current_amperes",
    "Charge current in A; kind is total, ac or dc.",
    ("vin", "kind"),
)
CHARGE_REMAINING = Gauge(
    "mazda6e_charge_remaining_seconds",
    "Estimated time until the charge limit is reached. Absent when no estimate exists.",
    _V,
)
CHARGE_STATE = Gauge(
    "mazda6e_charge_state",
    "1 for the current charge state (not_charging/charging/completed/paused/unknown), else 0.",
    ("vin", "state"),
)
CHARGING = Gauge("mazda6e_charging", "1 while the car is charging.", _V)
PLUGGED_IN = Gauge(
    "mazda6e_plugged_in",
    "1 if a charge cable is connected; connector is ac or dc.",
    ("vin", "connector"),
)

# --- body ---
DOOR_OPEN = Gauge("mazda6e_door_open", "1 if the door (or the trunk) is open.", ("vin", "door"))
WINDOW_OPEN = Gauge("mazda6e_window_open", "1 if the window is open.", ("vin", "window"))
WINDOW_OPEN_DEGREE = Gauge(
    "mazda6e_window_open_degree", "Window opening as reported by the car.", ("vin", "window")
)
UNLOCKED = Gauge("mazda6e_unlocked", "1 if this side's doors are unlocked.", ("vin", "side"))
LAMP_ON = Gauge("mazda6e_lamp_on", "1 if the exterior lamp is on.", ("vin", "lamp"))
TIRE_PRESSURE = Gauge("mazda6e_tire_pressure_kpa", "Tire pressure in kPa.", ("vin", "tire"))

# --- cabin ---
CABIN_TEMPERATURE = Gauge(
    "mazda6e_cabin_temperature_celsius",
    "Cabin temperature in degrees Celsius; sensor is inside or cockpit.",
    ("vin", "sensor"),
)
CLIMATE_TARGET = Gauge(
    "mazda6e_climate_target_temperature_celsius", "Remote climate target temperature.", _V
)
CABIN_HUMIDITY = Gauge("mazda6e_cabin_humidity_percent", "Cabin relative humidity in %.", _V)
CABIN_PM25 = Gauge("mazda6e_cabin_pm25_micrograms_per_cubic_meter", "Cabin PM2.5 in µg/m³.", _V)
CLIMATE_FEATURE = Gauge(
    "mazda6e_climate_feature_on",
    "1 if the feature (ac/defrost/steering_wheel_heater) is on.",
    ("vin", "feature"),
)
SEAT_MODE = Gauge(
    "mazda6e_seat_mode",
    "1 for the seat's current mode (off/heating/ventilation/unknown), else 0.",
    ("vin", "seat", "mode"),
)
SEAT_LEVEL = Gauge("mazda6e_seat_level", "Seat heating or ventilation level.", ("vin", "seat"))

# --- location (opt-in) ---
LATITUDE = Gauge("mazda6e_location_latitude_degrees", "Last reported latitude.", _V)
LONGITUDE = Gauge("mazda6e_location_longitude_degrees", "Last reported longitude.", _V)

# --- exporter health ---
SCRAPE_SUCCESS = Gauge(
    "mazda6e_scrape_success", "1 if the most recent poll of the Mazda cloud succeeded."
)
LAST_SUCCESS = Gauge(
    "mazda6e_last_success_timestamp_seconds", "Unix time of the most recent successful poll."
)
VEHICLES = Gauge("mazda6e_vehicles", "Number of vehicles on the account.")

# The API's position names, in the order its door/window arrays use.
POSITIONS = ("front_left", "front_right", "rear_left", "rear_right")
_SIDE_KEYS = {
    "front_left": "leftFront",
    "front_right": "rightFront",
    "rear_left": "leftBack",
    "rear_right": "rightBack",
}
_LAMPS = {
    "low_beam": "lowBeam",
    "high_beam": "highBeam",
    "position": "positionLamp",
    "left_turn": "leftTurn",
    "right_turn": "rightTurn",
}

CHARGE_STATES = {0: "not_charging", 4: "completed", 6: "charging", 7: "paused"}
POWER_STATES = {0: "off", 1: "accessory", 2: "on"}
VEHICLE_STATES = {1: "driving", 2: "parked"}
SEAT_MODES = {0: "off", 1: "heating", 2: "ventilation"}

# remainChargeTime is 0x1FFF when the car has no estimate.
NO_CHARGE_ESTIMATE = 8191

_LATITUDE_KEYS = ("latitude", "lat", "gpsLatitude")
_LONGITUDE_KEYS = ("longitude", "lng", "lon", "gpsLongitude")


def _get(data: Any, *path: str | int) -> Any:
    for key in path:
        if isinstance(data, dict):
            data = data.get(key)
        elif isinstance(data, list) and isinstance(key, int) and -len(data) <= key < len(data):
            data = data[key]
        else:
            return None
    return data


def _number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _flag(value: Any) -> float | None:
    """API booleans arrive as bool, 0/1 or "0"/"1"."""
    number = _number(value)
    return None if number is None else float(number != 0)


def _set(gauge: Gauge, value: float | None, *labels: str) -> None:
    if value is None:
        try:
            gauge.remove(*labels)
        except KeyError:
            pass
    else:
        gauge.labels(*labels).set(value)


def _set_enum(gauge: Gauge, vin: str, raw: Any, names: dict[int, str], *extra: str) -> None:
    """One series per possible state, 1 for the current one, so changes show at once."""
    number = _number(raw)
    current = names.get(int(number), "unknown") if number is not None else "unknown"
    for name in (*names.values(), "unknown"):
        gauge.labels(vin, *extra, name).set(1 if name == current else 0)


def _temperature(raw: Any) -> float | None:
    """Temperatures come in tenths of a degree; 0 means not measured."""
    number = _number(raw)
    return None if not number else number / 10


def _coordinate(location: Any, keys: Iterable[str]) -> float | None:
    if not isinstance(location, dict):
        return None
    for key in keys:
        number = _number(location.get(key))
        if number is not None:
            return number
    return None


def update_vehicle(vehicle: Vehicle, status: dict, *, export_location: bool = False) -> None:
    vin = vehicle.vin
    VEHICLE_INFO.labels(vin, vehicle.model, vehicle.name, vehicle.series).set(1)

    vs = status.get("vehicleStatus") or {}
    _set(SOC, _number(vs.get("soc")), vin)
    _set(RANGE, _number(vs.get("drvMileage")), vin)
    _set(ODOMETER, _number(vs.get("totalMileage")), vin)
    speed = _number(vs.get("speed"))
    # The car has been seen reporting junk speeds while parked.
    _set(SPEED, speed if speed is not None and 0 <= speed <= 250 else None, vin)
    _set(ONLINE, _flag(vs.get("connectStatus")), vin)
    _set_enum(POWER_STATE, vin, vs.get("powerStatus"), POWER_STATES)
    _set_enum(VEHICLE_STATE, vin, vs.get("status"), VEHICLE_STATES)
    _set(CLIMATE_FEATURE, _flag(vs.get("steeringWheelHeater")), vin, "steering_wheel_heater")

    updated = _number(status.get("lastUpdatedAt"))
    _set(STATUS_UPDATED, updated / 1000 if updated and updated > 0 else None, vin)

    charge = status.get("charge") or {}
    _set(CHARGE_TARGET, _number(charge.get("maxSocPercent")), vin)
    for kind, key in (
        ("total", "chargeCurrent"),
        ("ac", "acChargeCurrent"),
        ("dc", "dcChargeCurrent"),
    ):
        _set(CHARGE_CURRENT, _number(charge.get(key)), vin, kind)
    remaining = _number(charge.get("remainChargeTime"))
    _set(
        CHARGE_REMAINING,
        remaining * 60 if remaining is not None and 0 <= remaining < NO_CHARGE_ESTIMATE else None,
        vin,
    )
    _set_enum(CHARGE_STATE, vin, charge.get("chargeStatus"), CHARGE_STATES)
    charge_status = _number(charge.get("chargeStatus"))
    _set(CHARGING, None if charge_status is None else float(charge_status == 6), vin)
    for connector, key in (("ac", "chargeConStatus"), ("dc", "dcChargeGunConnectStatus")):
        _set(PLUGGED_IN, _flag(charge.get(key)), vin, connector)

    door = status.get("door") or {}
    window = status.get("window") or {}
    for i, position in enumerate(POSITIONS):
        _set(DOOR_OPEN, _flag(_get(door, "doors", i)), vin, position)
        _set(WINDOW_OPEN, _flag(_get(window, "windows", i)), vin, position)
        _set(WINDOW_OPEN_DEGREE, _number(_get(window, "openDegree", i)), vin, position)
    _set(DOOR_OPEN, _flag(door.get("trunk")), vin, "trunk")
    # driverLock/passengerLock read 1 right after a remote unlock.
    for side, key in (("driver", "driverLock"), ("passenger", "passengerLock")):
        lock = _number(door.get(key))
        _set(UNLOCKED, None if lock is None else float(lock == 1), vin, side)

    lamp = status.get("lamp") or {}
    for name, key in _LAMPS.items():
        _set(LAMP_ON, _flag(lamp.get(key)), vin, name)

    for position, key in _SIDE_KEYS.items():
        _set(TIRE_PRESSURE, _number(_get(status, "tire", key, "pressure")), vin, position)
        seat = _get(status, "seat", key)
        if isinstance(seat, dict):
            _set_enum(SEAT_MODE, vin, seat.get("mode"), SEAT_MODES, position)
            _set(SEAT_LEVEL, _number(seat.get("level")), vin, position)

    hvac = status.get("hvac") or {}
    _set(CABIN_TEMPERATURE, _temperature(hvac.get("insideTemp")), vin, "inside")
    _set(CABIN_TEMPERATURE, _temperature(hvac.get("consTempCockpit")), vin, "cockpit")
    _set(CLIMATE_TARGET, _temperature(hvac.get("remoteTemp")), vin)
    _set(CABIN_HUMIDITY, _number(hvac.get("insideHumidity")), vin)
    _set(CABIN_PM25, _number(hvac.get("insidePm25")), vin)
    _set(CLIMATE_FEATURE, _flag(hvac.get("acStatus")), vin, "ac")
    _set(CLIMATE_FEATURE, _flag(hvac.get("defrostStatus")), vin, "defrost")

    location = status.get("location")
    lat = _coordinate(location, _LATITUDE_KEYS) if export_location else None
    lon = _coordinate(location, _LONGITUDE_KEYS) if export_location else None
    # Publish a position only as a pair; one coordinate on its own is useless.
    if lat is None or lon is None:
        lat = lon = None
    _set(LATITUDE, lat, vin)
    _set(LONGITUDE, lon, vin)
