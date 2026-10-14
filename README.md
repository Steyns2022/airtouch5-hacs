# AirTouch 5 (status sensors) — Home Assistant custom integration

A fork of Home Assistant's built-in [AirTouch 5](https://www.home-assistant.io/integrations/airtouch5)
integration (copied from Home Assistant `2026.10.1`, original code by
[@danzel](https://github.com/danzel)). It keeps the same domain, `airtouch5`, so it
replaces the built-in integration in place: the existing config entry, climate
entities and damper covers carry on unchanged.

## What it adds

The AirTouch 5 console reports these in every status packet; the built-in
integration doesn't expose them.

| Entity | Device | Meaning |
| --- | --- | --- |
| `sensor.<ac>_error_code` | AC | The unit's error code; `0` = no error |
| `binary_sensor.<ac>_fault` | AC | On when the error code isn't `0` (device class *problem*) |
| `binary_sensor.<ac>_spill` | AC | Spill active (air dumped into spill zones) |
| `binary_sensor.<ac>_bypass` | AC | Bypass damper active |
| `binary_sensor.<ac>_turbo` | AC | Turbo active |
| `binary_sensor.<zone>_sensor_battery` | Zone | Wireless temperature sensor battery low (only zones with a sensor) |
| `binary_sensor.<zone>_spill` | Zone | This zone is receiving spill air |

There is no power or energy data: the AirTouch 5 protocol doesn't report it.

## Install (HACS)

1. HACS → ⋮ → Custom repositories → add this repository as an *Integration*.
2. Download **AirTouch 5 (status sensors)**, then restart Home Assistant.
3. The new entities appear on the existing AirTouch 5 devices. Home Assistant logs a
   warning that a custom integration overrides the built-in `airtouch5`; that is expected.

To go back to the built-in integration, remove it in HACS and restart.

## Keeping up with Home Assistant

This copy is pinned to the `2026.10.1` code. When a Home Assistant release changes
the built-in `airtouch5` integration, diff it against `custom_components/airtouch5/`
and carry the changes over. The fork's own additions are `binary_sensor.py`,
`sensor.py`, the `PLATFORMS` list in `__init__.py`, `manifest.json` and `translations/`.

## Tests

```bash
uv venv --python 3.14 .venv
uv pip install --python .venv/bin/python "pytest-homeassistant-custom-component==0.13.372" "airtouch5py==0.4.0"
.venv/bin/python -m pytest -q
```

Licensed under the Apache License 2.0, like Home Assistant (see `LICENSE`).
