"""The fork's status sensors, next to the unchanged climate and cover entities."""

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .conftest import ac_status, zone_status


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain="airtouch5", data={CONF_HOST: "192.0.2.10"}, unique_id="192.0.2.10")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_entities_created(hass: HomeAssistant, fake_client) -> None:
    entry = await _setup(hass)
    assert entry.state is ConfigEntryState.LOADED
    assert hass.states.get("sensor.ac_0_error_code").state == "0"
    for flag in ("fault", "spill", "bypass", "turbo"):
        assert hass.states.get(f"binary_sensor.ac_0_{flag}").state == "off", flag
    assert hass.states.get("binary_sensor.ac_0_fault").attributes["device_class"] == "problem"
    assert hass.states.get("binary_sensor.library_sensor_battery").state == "off"
    assert hass.states.get("binary_sensor.library_sensor_battery").attributes["device_class"] == "battery"
    assert hass.states.get("binary_sensor.hallway_spill").state == "off"
    # No wireless sensor in the hallway, so no battery entity there.
    assert hass.states.get("binary_sensor.hallway_sensor_battery") is None
    # The built-in platforms are still there.
    assert hass.states.get("climate.ac_0").state == "heat"
    assert hass.states.get("climate.library") is not None
    assert hass.states.get("cover.library_damper").attributes["current_position"] == 80


async def test_ac_flags_follow_status(hass: HomeAssistant, fake_client) -> None:
    await _setup(hass)
    client = fake_client["client"]
    client.push_ac(ac_status(error_code=7, spill_active=True, bypass_active=True, turbo_active=True))
    await hass.async_block_till_done()
    assert hass.states.get("sensor.ac_0_error_code").state == "7"
    for flag in ("fault", "spill", "bypass", "turbo"):
        assert hass.states.get(f"binary_sensor.ac_0_{flag}").state == "on", flag
    client.push_ac(ac_status())
    await hass.async_block_till_done()
    assert hass.states.get("binary_sensor.ac_0_fault").state == "off"
    assert hass.states.get("sensor.ac_0_error_code").state == "0"


async def test_zone_flags_follow_status(hass: HomeAssistant, fake_client) -> None:
    await _setup(hass)
    client = fake_client["client"]
    client.push_zones(zone_status(1, is_low_battery=True, spill_active=True))
    await hass.async_block_till_done()
    assert hass.states.get("binary_sensor.kitchen_sensor_battery").state == "on"
    assert hass.states.get("binary_sensor.kitchen_spill").state == "on"
    assert hass.states.get("binary_sensor.library_sensor_battery").state == "off"


async def test_unload_removes_listeners(hass: HomeAssistant, fake_client) -> None:
    entry = await _setup(hass)
    client = fake_client["client"]
    assert client.ac_status_callbacks and client.zone_status_callbacks
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
    assert client.ac_status_callbacks == [] and client.zone_status_callbacks == []
