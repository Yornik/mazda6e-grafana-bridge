# mazda6e-grafana-bridge

A Prometheus exporter for the **Mazda 6e** cloud API, plus a Grafana dashboard
for it. It logs in with the Mazda app account, polls the car's condition on an
interval and publishes battery, charging, driving, body, cabin and tire state
as Prometheus metrics.

- **Read-only.** It can't lock, unlock, open, climate-control or charge-limit
  the car. The command endpoints were left out of the code.
- **Stateless.** Configuration comes from environment variables only. Tokens
  live in memory. An expired token is refreshed, and a refused refresh falls
  back to a new password login with the same device ID.
- **Fails safe.** A failed poll sets `mazda6e_scrape_success` to `0` instead of
  crashing the process. After a refused login it waits an hour before it tries
  the password again, so a mistake can't lock the account.

The API knowledge (endpoints, headers, credential encryption, field meanings)
comes from [fano0001/home-assistant-mazda-6e](https://github.com/fano0001/home-assistant-mazda-6e),
the Home Assistant integration. See [NOTICE](NOTICE).

## Metrics

All per-vehicle series carry a `vin` label.

| Metric | Extra labels | Description |
| --- | --- | --- |
| `mazda6e_vehicle_info` | `model`, `name`, `series` | Always `1`. Gives the car's descriptive labels. |
| `mazda6e_battery_soc_percent` | | State of charge in % |
| `mazda6e_range_km` | | Remaining range in km |
| `mazda6e_odometer_km` | | Odometer in km |
| `mazda6e_speed_kmh` | | Speed in km/h. Implausible values over 250 are dropped. |
| `mazda6e_vehicle_state` | `state` | One-hot: `driving` / `parked` / `unknown` |
| `mazda6e_power_state` | `state` | One-hot: `off` / `accessory` / `on` / `unknown` |
| `mazda6e_online` | | `1` if the car is connected to the Mazda cloud |
| `mazda6e_status_updated_timestamp_seconds` | | When the car last reported to the cloud |
| `mazda6e_charge_state` | `state` | One-hot: `not_charging` / `charging` / `completed` / `paused` / `unknown` |
| `mazda6e_charging` | | `1` while charging |
| `mazda6e_charge_target_soc_percent` | | Charge limit in % |
| `mazda6e_charge_current_amperes` | `kind` | `total`, `ac`, `dc` |
| `mazda6e_charge_remaining_seconds` | | Time until the limit is reached. Absent when the car has no estimate. |
| `mazda6e_plugged_in` | `connector` | `ac`, `dc` |
| `mazda6e_door_open` | `door` | `front_left`, `front_right`, `rear_left`, `rear_right`, `trunk` |
| `mazda6e_window_open` / `mazda6e_window_open_degree` | `window` | Same positions as doors |
| `mazda6e_unlocked` | `side` | `driver`, `passenger` |
| `mazda6e_lamp_on` | `lamp` | `low_beam`, `high_beam`, `position`, `left_turn`, `right_turn` |
| `mazda6e_tire_pressure_kpa` | `tire` | Same positions as doors, without the trunk |
| `mazda6e_cabin_temperature_celsius` | `sensor` | `inside`, `cockpit` |
| `mazda6e_climate_target_temperature_celsius` | | Remote climate target |
| `mazda6e_cabin_humidity_percent` | | Cabin humidity |
| `mazda6e_cabin_pm25_micrograms_per_cubic_meter` | | Cabin PM2.5 |
| `mazda6e_climate_feature_on` | `feature` | `ac`, `defrost`, `steering_wheel_heater` |
| `mazda6e_seat_mode` / `mazda6e_seat_level` | `seat`, (`mode`) | Seat heating/ventilation |
| `mazda6e_location_latitude_degrees` / `..._longitude_degrees` | | Only with `EXPORT_LOCATION=true` |
| `mazda6e_scrape_success` | — | `1` if the last poll succeeded |
| `mazda6e_last_success_timestamp_seconds` | — | Time of the last successful poll |
| `mazda6e_vehicle_scrape_success` | | Per-vehicle result of the last poll |
| `mazda6e_vehicles` | — | Vehicles on the account |

The exporter only publishes fields the car actually reports. If a field
disappears, its series is removed, so a missing reading never shows as `0`.

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `MAZDA_EMAIL` | _(required)_ | Mazda app account email |
| `MAZDA_PASSWORD` | _(required)_ | Mazda app account password |
| `MAZDA_DEVICE_ID` | _(required)_ | A UUID that identifies this exporter to Mazda. Generate it once and keep it. |
| `POLL_INTERVAL_SECONDS` | `300` | Seconds between polls (minimum 60) |
| `LISTEN_PORT` | `9120` | Port the `/metrics` endpoint listens on |
| `EXPORT_LOCATION` | `false` | Publish the car's GPS position |
| `REQUEST_TIMEOUT_SECONDS` | `30` | Timeout for each HTTP call to Mazda |
| `MAZDA_API_BASE_URL` | Europe backend | Override for testing only |

Only the **Europe** backend is supported. Asian accounts read their status over
MQTT, which this exporter doesn't implement.

## First run: verify the device

Mazda emails a code the first time a new device ID signs in. Do this once,
interactively, with the same `MAZDA_DEVICE_ID` the exporter will use:

```bash
export MAZDA_DEVICE_ID=$(python3 -c 'import uuid; print(uuid.uuid4())')   # keep this value
docker run --rm -it \
  -e MAZDA_EMAIL -e MAZDA_PASSWORD -e MAZDA_DEVICE_ID \
  ghcr.io/yornik/mazda6e-grafana-bridge:latest verify-device
```

After that, the exporter logs in on its own. If the device ID changes, you
have to verify again.

## Run with Docker

```bash
docker run --rm -p 9120:9120 \
  -e MAZDA_EMAIL -e MAZDA_PASSWORD -e MAZDA_DEVICE_ID \
  ghcr.io/yornik/mazda6e-grafana-bridge:latest

curl -s localhost:9120/metrics | grep ^mazda6e_
```

## Grafana dashboard

![The Mazda 6e dashboard, rendered with test data](docs/dashboard.png)

[`dashboards/mazda6e.json`](dashboards/mazda6e.json) has these sections:

- **Overview:** state of charge, range, charge state, locks, odometer and data age.
- **Battery & charging:** SoC against the charge limit, range, AC/DC current,
  plug/charge timeline and time to limit.
- **Driving:** distance per day, vehicle and power state, speed.
- **Body:** door, trunk, window, lock and lamp timelines.
- **Tires:** current pressures and history.
- **Cabin:** temperatures, humidity, PM2.5, climate and seat timelines.
- **Location:** last known position. Needs `EXPORT_LOCATION=true`.
- **Exporter:** poll health.

To import it, go to **Dashboards → New → Import**, upload the file and pick
your Prometheus data source. To provision it with the kube-prometheus-stack
Grafana sidecar, wrap the file in a `ConfigMap` labelled `grafana_dashboard: "1"`.

## Kubernetes

Run it like `dirigera-exporter`: a Deployment, a Service and a ServiceMonitor,
with the credentials in a SOPS-encrypted Secret. The image runs as uid 65532
with a read-only root filesystem and needs no volume. The manifests belong in
the GitOps repo, not here. This repo builds the image and holds the dashboard.

## Development

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
ruff check . && ruff format --check . && pytest
```

The tests mock the Mazda API and need no account or car.

### CI

[`checks.yaml`](.github/workflows/checks.yaml) holds every check. It runs on
pull requests and on `main`, and again on the release commit before an image
is published:

| Job | What it checks |
| --- | --- |
| Lint | `ruff check`, `ruff format`, `actionlint`, `hadolint` |
| Test | `pytest` with coverage in the run summary. The tests also check that every metric the dashboard queries is exported. |
| Dashboard | Runs every dashboard query through `promtool`, the Prometheus parser |
| Audit | `pip-audit` over the runtime dependencies |
| Image | Builds the image, then runs it read-only as non-root against an unreachable API and checks that it serves `/metrics` and reports the failed poll |

Releases are cut by release-please from Conventional Commits and pushed to
`ghcr.io/yornik/mazda6e-grafana-bridge` with an SBOM and provenance. Every
action is pinned to a commit digest. Renovate keeps the digests and tool
versions current, with a three-day minimum release age.

## Disclaimer & trademarks

This is an independent, unofficial project. Mazda Motor Corporation and
Changan Automobile don't affiliate with, authorize, sponsor or endorse it.
**Mazda** and **Mazda 6e** are trademarks of Mazda Motor Corporation. They are
used here only to identify the vehicle this software works with.

The exporter talks to the same cloud API as the official app, using your own
account. Mazda can change or restrict that API at any time.

## License

[Apache-2.0](LICENSE). This repo contains code adapted from an Apache-2.0
project. See [NOTICE](NOTICE).
