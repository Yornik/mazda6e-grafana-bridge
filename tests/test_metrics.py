from __future__ import annotations

from conftest import VEHICLE, VIN, sample

from mazda6e_bridge import metrics


def test_maps_battery_range_and_driving(status):
    metrics.update_vehicle(VEHICLE, status)

    assert sample("mazda6e_battery_soc_percent", vin=VIN) == 81
    assert sample("mazda6e_range_km", vin=VIN) == 402
    assert sample("mazda6e_odometer_km", vin=VIN) == 12345
    assert sample("mazda6e_speed_kmh", vin=VIN) == 0
    assert sample("mazda6e_online", vin=VIN) == 1
    assert sample("mazda6e_status_updated_timestamp_seconds", vin=VIN) == 1760000000
    assert (
        sample("mazda6e_vehicle_info", vin=VIN, model="Mazda 6e", name="Shark", series="Takumi")
        == 1
    )


def test_enums_publish_one_hot(status):
    metrics.update_vehicle(VEHICLE, status)

    assert sample("mazda6e_vehicle_state", vin=VIN, state="parked") == 1
    assert sample("mazda6e_vehicle_state", vin=VIN, state="driving") == 0
    assert sample("mazda6e_power_state", vin=VIN, state="off") == 1
    assert sample("mazda6e_charge_state", vin=VIN, state="charging") == 1
    assert sample("mazda6e_charge_state", vin=VIN, state="unknown") == 0
    assert sample("mazda6e_seat_mode", vin=VIN, seat="front_left", mode="heating") == 1


def test_unknown_enum_value_maps_to_unknown(status):
    status["charge"]["chargeStatus"] = 99
    metrics.update_vehicle(VEHICLE, status)

    assert sample("mazda6e_charge_state", vin=VIN, state="unknown") == 1
    assert sample("mazda6e_charge_state", vin=VIN, state="charging") == 0
    assert sample("mazda6e_charging", vin=VIN) == 0


def test_charging(status):
    metrics.update_vehicle(VEHICLE, status)

    assert sample("mazda6e_charging", vin=VIN) == 1
    assert sample("mazda6e_charge_target_soc_percent", vin=VIN) == 90
    assert sample("mazda6e_charge_current_amperes", vin=VIN, kind="ac") == 15.5
    assert sample("mazda6e_charge_remaining_seconds", vin=VIN) == 45 * 60
    assert sample("mazda6e_plugged_in", vin=VIN, connector="ac") == 1
    assert sample("mazda6e_plugged_in", vin=VIN, connector="dc") == 0


def test_no_charge_estimate_removes_the_series(status):
    metrics.update_vehicle(VEHICLE, status)
    status["charge"]["remainChargeTime"] = metrics.NO_CHARGE_ESTIMATE
    metrics.update_vehicle(VEHICLE, status)

    assert sample("mazda6e_charge_remaining_seconds", vin=VIN) is None


def test_body(status):
    metrics.update_vehicle(VEHICLE, status)

    assert sample("mazda6e_door_open", vin=VIN, door="front_right") == 1
    assert sample("mazda6e_door_open", vin=VIN, door="front_left") == 0
    assert sample("mazda6e_door_open", vin=VIN, door="trunk") == 0
    assert sample("mazda6e_window_open", vin=VIN, window="rear_left") == 1
    assert sample("mazda6e_window_open_degree", vin=VIN, window="rear_left") == 30
    assert sample("mazda6e_unlocked", vin=VIN, side="driver") == 0
    assert sample("mazda6e_lamp_on", vin=VIN, lamp="position") == 1
    assert sample("mazda6e_tire_pressure_kpa", vin=VIN, tire="rear_right") == 259


def test_unlocked_reads_one(status):
    status["door"]["driverLock"] = 1
    metrics.update_vehicle(VEHICLE, status)

    assert sample("mazda6e_unlocked", vin=VIN, side="driver") == 1
    assert sample("mazda6e_unlocked", vin=VIN, side="passenger") == 0


def test_cabin_temperatures_are_tenths_and_zero_means_absent(status):
    metrics.update_vehicle(VEHICLE, status)

    assert sample("mazda6e_cabin_temperature_celsius", vin=VIN, sensor="inside") == 21.5
    assert sample("mazda6e_cabin_temperature_celsius", vin=VIN, sensor="cockpit") is None
    assert sample("mazda6e_climate_target_temperature_celsius", vin=VIN) == 22.0
    assert sample("mazda6e_cabin_humidity_percent", vin=VIN) == 48
    assert sample("mazda6e_cabin_pm25_micrograms_per_cubic_meter", vin=VIN) == 7
    assert sample("mazda6e_climate_feature_on", vin=VIN, feature="ac") == 1
    assert sample("mazda6e_climate_feature_on", vin=VIN, feature="steering_wheel_heater") == 0


def test_implausible_speed_is_dropped(status):
    status["vehicleStatus"]["speed"] = 4000
    metrics.update_vehicle(VEHICLE, status)

    assert sample("mazda6e_speed_kmh", vin=VIN) is None


def test_location_is_opt_in(status):
    metrics.update_vehicle(VEHICLE, status)
    assert sample("mazda6e_location_latitude_degrees", vin=VIN) is None

    metrics.update_vehicle(VEHICLE, status, export_location=True)
    assert sample("mazda6e_location_latitude_degrees", vin=VIN) == 52.0907
    assert sample("mazda6e_location_longitude_degrees", vin=VIN) == 5.1214


def test_half_a_position_is_not_published(status):
    del status["location"]["longitude"]
    metrics.update_vehicle(VEHICLE, status, export_location=True)

    assert sample("mazda6e_location_latitude_degrees", vin=VIN) is None


def test_missing_sections_do_not_raise_or_publish_zeroes():
    metrics.update_vehicle(VEHICLE, {"vehicleStatus": {"soc": 50}})

    assert sample("mazda6e_battery_soc_percent", vin=VIN) == 50
    assert sample("mazda6e_range_km", vin=VIN) is None
    assert sample("mazda6e_door_open", vin=VIN, door="front_left") is None
    assert sample("mazda6e_tire_pressure_kpa", vin=VIN, tire="front_left") is None


def test_field_that_disappears_removes_its_series(status):
    metrics.update_vehicle(VEHICLE, status)
    del status["hvac"]["insidePm25"]
    metrics.update_vehicle(VEHICLE, status)

    assert sample("mazda6e_cabin_pm25_micrograms_per_cubic_meter", vin=VIN) is None


def test_string_values_are_accepted(status):
    status["vehicleStatus"]["soc"] = "77"
    status["vehicleStatus"]["drvMileage"] = "n/a"
    metrics.update_vehicle(VEHICLE, status)

    assert sample("mazda6e_battery_soc_percent", vin=VIN) == 77
    assert sample("mazda6e_range_km", vin=VIN) is None
