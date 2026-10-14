"""Binary sensors for AirTouch 5 status flags (fork addition).

The console reports these in every AC / zone status packet, but Home
Assistant's built-in integration doesn't expose them: an AC fault (error code
other than 0), spill, bypass and turbo on the AC, and spill plus a low wireless
sensor battery on each zone.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import override

from airtouch5py.airtouch5_simple_client import Airtouch5SimpleClient
from airtouch5py.packets.ac_ability import AcAbility
from airtouch5py.packets.ac_status import AcStatus
from airtouch5py.packets.zone_name import ZoneName
from airtouch5py.packets.zone_status import ZoneStatusZone

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import Airtouch5ConfigEntry
from .const import DOMAIN
from .entity import Airtouch5Entity


@dataclass(frozen=True, kw_only=True)
class Airtouch5AcBinarySensorDescription(BinarySensorEntityDescription):
    """Describes an AC status flag."""

    value_fn: Callable[[AcStatus], bool]


@dataclass(frozen=True, kw_only=True)
class Airtouch5ZoneBinarySensorDescription(BinarySensorEntityDescription):
    """Describes a zone status flag."""

    value_fn: Callable[[ZoneStatusZone], bool]
    needs_sensor: bool = False


AC_BINARY_SENSORS: tuple[Airtouch5AcBinarySensorDescription, ...] = (
    Airtouch5AcBinarySensorDescription(
        key="fault",
        name="Fault",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda status: status.error_code != 0,
    ),
    Airtouch5AcBinarySensorDescription(
        key="spill",
        name="Spill",
        icon="mdi:call-split",
        value_fn=lambda status: status.spill_active,
    ),
    Airtouch5AcBinarySensorDescription(
        key="bypass",
        name="Bypass",
        icon="mdi:swap-horizontal",
        value_fn=lambda status: status.bypass_active,
    ),
    Airtouch5AcBinarySensorDescription(
        key="turbo",
        name="Turbo",
        icon="mdi:fan-plus",
        value_fn=lambda status: status.turbo_active,
    ),
)

ZONE_BINARY_SENSORS: tuple[Airtouch5ZoneBinarySensorDescription, ...] = (
    Airtouch5ZoneBinarySensorDescription(
        key="sensor_battery",
        name="Sensor battery",
        device_class=BinarySensorDeviceClass.BATTERY,
        entity_category=EntityCategory.DIAGNOSTIC,
        needs_sensor=True,
        value_fn=lambda zone: zone.is_low_battery,
    ),
    Airtouch5ZoneBinarySensorDescription(
        key="spill",
        name="Spill",
        icon="mdi:call-split",
        value_fn=lambda zone: zone.spill_active,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: Airtouch5ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Airtouch 5 binary sensors."""
    client = config_entry.runtime_data
    entities: list[BinarySensorEntity] = [
        Airtouch5AcBinarySensor(client, ac, description)
        for ac in client.ac
        for description in AC_BINARY_SENSORS
    ]
    for zone in client.zones:
        status = client.latest_zone_status.get(zone.zone_number)
        has_sensor = bool(status and status.has_sensor)
        entities.extend(
            Airtouch5ZoneBinarySensor(client, zone, description)
            for description in ZONE_BINARY_SENSORS
            if has_sensor or not description.needs_sensor
        )
    async_add_entities(entities)


class Airtouch5AcBinarySensor(BinarySensorEntity, Airtouch5Entity):
    """A status flag of the AC unit."""

    entity_description: Airtouch5AcBinarySensorDescription

    def __init__(
        self,
        client: Airtouch5SimpleClient,
        ability: AcAbility,
        description: Airtouch5AcBinarySensorDescription,
    ) -> None:
        """Initialise the binary sensor."""
        super().__init__(client)
        self.entity_description = description
        self._ac_number = ability.ac_number
        self._attr_unique_id = f"ac_{ability.ac_number}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"ac_{ability.ac_number}")},
            name=f"AC {ability.ac_number}",
            manufacturer="Polyaire",
            model="AirTouch 5",
        )

    @callback
    def _async_update_attrs(self, data: dict[int, AcStatus]) -> None:
        if self._ac_number not in data:
            return
        self._attr_is_on = self.entity_description.value_fn(data[self._ac_number])
        self.async_write_ha_state()

    @override
    async def async_added_to_hass(self) -> None:
        """Listen for AC status packets."""
        await super().async_added_to_hass()
        self._client.ac_status_callbacks.append(self._async_update_attrs)
        self._async_update_attrs(self._client.latest_ac_status)

    @override
    async def async_will_remove_from_hass(self) -> None:
        """Stop listening for AC status packets."""
        await super().async_will_remove_from_hass()
        self._client.ac_status_callbacks.remove(self._async_update_attrs)


class Airtouch5ZoneBinarySensor(BinarySensorEntity, Airtouch5Entity):
    """A status flag of one zone."""

    entity_description: Airtouch5ZoneBinarySensorDescription

    def __init__(
        self,
        client: Airtouch5SimpleClient,
        zone_name: ZoneName,
        description: Airtouch5ZoneBinarySensorDescription,
    ) -> None:
        """Initialise the binary sensor."""
        super().__init__(client)
        self.entity_description = description
        self._zone_number = zone_name.zone_number
        self._attr_unique_id = f"zone_{zone_name.zone_number}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"zone_{zone_name.zone_number}")},
            name=zone_name.zone_name,
            manufacturer="Polyaire",
            model="AirTouch 5",
        )

    @callback
    def _async_update_attrs(self, data: dict[int, ZoneStatusZone]) -> None:
        if self._zone_number not in data:
            return
        self._attr_is_on = self.entity_description.value_fn(data[self._zone_number])
        self.async_write_ha_state()

    @override
    async def async_added_to_hass(self) -> None:
        """Listen for zone status packets."""
        await super().async_added_to_hass()
        self._client.zone_status_callbacks.append(self._async_update_attrs)
        self._async_update_attrs(self._client.latest_zone_status)

    @override
    async def async_will_remove_from_hass(self) -> None:
        """Stop listening for zone status packets."""
        await super().async_will_remove_from_hass()
        self._client.zone_status_callbacks.remove(self._async_update_attrs)
