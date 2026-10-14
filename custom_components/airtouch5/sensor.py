"""Error code sensor for the AirTouch 5 AC unit (fork addition).

0 means no error. Any other value is the unit's fault code as shown on the
AirTouch console; look it up in the AC manufacturer's error table.
"""

from typing import override

from airtouch5py.airtouch5_simple_client import Airtouch5SimpleClient
from airtouch5py.packets.ac_ability import AcAbility
from airtouch5py.packets.ac_status import AcStatus

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import Airtouch5ConfigEntry
from .const import DOMAIN
from .entity import Airtouch5Entity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: Airtouch5ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Airtouch 5 sensors."""
    client = config_entry.runtime_data
    async_add_entities(Airtouch5AcErrorCode(client, ac) for ac in client.ac)


class Airtouch5AcErrorCode(SensorEntity, Airtouch5Entity):
    """The AC unit's error code (0 = no error)."""

    _attr_name = "Error code"
    _attr_icon = "mdi:alert-circle-outline"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, client: Airtouch5SimpleClient, ability: AcAbility) -> None:
        """Initialise the sensor."""
        super().__init__(client)
        self._ac_number = ability.ac_number
        self._attr_unique_id = f"ac_{ability.ac_number}_error_code"
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
        self._attr_native_value = data[self._ac_number].error_code
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
