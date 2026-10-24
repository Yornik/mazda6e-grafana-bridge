# Changelog

## [1.2.0](https://github.com/Yornik/mazda6e-grafana-bridge/compare/v1.1.0...v1.2.0) (2026-10-24)


### Features

* **dashboard:** add "Battery current while driving" ([1bd09de](https://github.com/Yornik/mazda6e-grafana-bridge/commit/1bd09de60fc88f06a8a6909e0c94e010b83d590e))
* **dashboard:** battery current while driving, and clearer charging current ([1bc8f43](https://github.com/Yornik/mazda6e-grafana-bridge/commit/1bc8f437fdcfa2f12eb374c64da5083e53a3adac))
* **dashboard:** clearer charging and driving current panels ([0f33ad2](https://github.com/Yornik/mazda6e-grafana-bridge/commit/0f33ad2cccd088b44553aee73ca1f26f78986bb5))
* **dashboard:** show charging and driving power in kW, not amps ([a21d589](https://github.com/Yornik/mazda6e-grafana-bridge/commit/a21d58908f129431906e93e65e02f5833cac03ad))
* **dashboard:** show charging and driving power in kW, not amps ([5d08743](https://github.com/Yornik/mazda6e-grafana-bridge/commit/5d087438783c82b915af52a4f1f62574b54dae13))


### Bug Fixes

* **dashboard:** keep short charge sessions at long ranges ([d475b63](https://github.com/Yornik/mazda6e-grafana-bridge/commit/d475b63f30867e92e982b1578de4abe1f74da8ae))
* **dashboard:** keep whole numbers on the kW axes ([4d7cfc5](https://github.com/Yornik/mazda6e-grafana-bridge/commit/4d7cfc52fd0e695c88b61f61360e21bf71f06818))
* **dashboard:** make the voltages settable from the URL ([cf5986d](https://github.com/Yornik/mazda6e-grafana-bridge/commit/cf5986d3f204915351811f5ad6fa7d272197ac62))

## [1.1.0](https://github.com/Yornik/mazda6e-grafana-bridge/compare/v1.0.0...v1.1.0) (2026-10-23)


### Features

* charger and battery current, raw charge status, dashboard fixes from real data ([9daaa26](https://github.com/Yornik/mazda6e-grafana-bridge/commit/9daaa26145e00d2316c26d75e21faacd3825f3f0))
* **metrics:** export charger and battery current, and the raw charge status ([a748b28](https://github.com/Yornik/mazda6e-grafana-bridge/commit/a748b28146efcd97311845aac42d38b1f71d1cd8))


### Bug Fixes

* **dashboard:** "Not charging" in Time to limit whenever the car is not charging ([2aa8e64](https://github.com/Yornik/mazda6e-grafana-bridge/commit/2aa8e64a52427b1e6cad75bc96bcab0e0bedb687))
* **dashboard:** correct charging current, distance per day and data age ([42b5371](https://github.com/Yornik/mazda6e-grafana-bridge/commit/42b537149bce6f0c4fdede3a5807b2b34a074d40))
* **dashboard:** drop the Speed panel and say "Not charging" instead of No data ([fd49091](https://github.com/Yornik/mazda6e-grafana-bridge/commit/fd49091855ab7862b695b398a11bd4e6534f349d))
* **dashboard:** drop the Speed panel and say "Not charging" instead of No data ([7c0c5e6](https://github.com/Yornik/mazda6e-grafana-bridge/commit/7c0c5e66c613dc86ea1feabdcb810f3ef5aa935f))
* **dashboard:** show the last 7 days in Distance per day; correct the speed note ([9c90a59](https://github.com/Yornik/mazda6e-grafana-bridge/commit/9c90a59a91994c6d7b39782addfbad2f465ed4da))

## 1.0.0 (2026-10-13)


### Features

* enforce read-only access and document the credential risk ([3ffc483](https://github.com/Yornik/mazda6e-grafana-bridge/commit/3ffc4832c0c6419c1863000a2fe9051be5c3aa30))
* Mazda 6e Prometheus exporter and Grafana dashboard ([5152b23](https://github.com/Yornik/mazda6e-grafana-bridge/commit/5152b23ce6b55df2d94bbb43a4a2e4d977ec25bf))
* Mazda 6e Prometheus exporter and Grafana dashboard ([d3b0525](https://github.com/Yornik/mazda6e-grafana-bridge/commit/d3b0525b6eba662ba37aa004819c4e86aa03d68e))
