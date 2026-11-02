"""The Airtouch 5 integration."""

from airtouch5py.airtouch5_simple_client import Airtouch5SimpleClient

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

# Fork: binary_sensor and sensor expose the status flags and error code.
PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.COVER,
    Platform.SENSOR,
]

type Airtouch5ConfigEntry = ConfigEntry[Airtouch5SimpleClient]


async def async_setup_entry(hass: HomeAssistant, entry: Airtouch5ConfigEntry) -> bool:
    """Set up Airtouch 5 from a config entry."""

    # Create API instance
    host = entry.data[CONF_HOST]
    client = Airtouch5SimpleClient(host)

    # Connect to the API
    try:
        await client.connect_and_stay_connected()
    except Exception as err:
        # Fork: core only retries on TimeoutError, so a refused or unreachable
        # console needed a manual reload. The library also raises a bare
        # Exception if the console hangs up mid-setup, so catch everything.
        # Close any open socket too, or each retry leaves a connection behind.
        # This reaches into the inner client because neither disconnect() is
        # safe here: the simple client's _connection_task only exists after
        # setup succeeds, and the inner client's _reader_task after it connects.
        if client._client._writer is not None:  # noqa: SLF001
            await client._client.disconnect()  # noqa: SLF001
        raise ConfigEntryNotReady(f"Can't connect to {host}: {err!r}") from err

    # Store an API object for your platforms to access
    entry.runtime_data = client

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: Airtouch5ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        client = entry.runtime_data
        await client.disconnect()
        client.ac_status_callbacks.clear()
        client.connection_state_callbacks.clear()
        client.data_packet_callbacks.clear()
        client.zone_status_callbacks.clear()

    return unload_ok
