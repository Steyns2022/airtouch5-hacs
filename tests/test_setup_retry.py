"""Setup failures must retry on their own and leave no connection open.

These use the real Airtouch5SimpleClient with only the socket faked, because
the failures depend on what the library raises and when.
"""

import asyncio
from datetime import timedelta
import errno
from unittest.mock import AsyncMock, MagicMock, patch

from airtouch5py.airtouch5_simple_client import Airtouch5SimpleClient
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

OPEN_CONNECTION = "airtouch5py.airtouch5_client.asyncio.open_connection"


def _writer() -> MagicMock:
    writer = MagicMock()
    writer.drain = AsyncMock()
    writer.wait_closed = AsyncMock()
    return writer


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain="airtouch5", data={CONF_HOST: "192.0.2.10"}, unique_id="192.0.2.10")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


@pytest.mark.parametrize(
    "error",
    [
        ConnectionRefusedError(errno.ECONNREFUSED, "Connect call failed"),
        OSError(errno.EHOSTUNREACH, "Connect call failed"),
        TimeoutError(),
    ],
    ids=["refused", "no_route", "timeout"],
)
async def test_connect_failure_retries(hass: HomeAssistant, error: Exception) -> None:
    """The console being off or refusing is temporary, not a broken setup."""
    with patch(OPEN_CONNECTION, side_effect=error):
        entry = await _setup(hass)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_disconnect_during_handshake_retries(hass: HomeAssistant) -> None:
    """The library raises a bare Exception if the console hangs up mid-setup."""
    reader = asyncio.StreamReader()
    reader.feed_eof()
    with patch(OPEN_CONNECTION, return_value=(reader, _writer())):
        entry = await _setup(hass)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_failed_handshake_closes_connection(hass: HomeAssistant) -> None:
    """A console that accepts but never answers must not keep a socket open."""
    writer = _writer()
    with (
        patch(OPEN_CONNECTION, return_value=(asyncio.StreamReader(), writer)),
        patch.object(Airtouch5SimpleClient, "_wait_for_packet_or_throw", side_effect=TimeoutError),
    ):
        entry = await _setup(hass)
    assert entry.state is ConfigEntryState.SETUP_RETRY
    writer.close.assert_called_once()


async def test_recovers_when_console_returns(hass: HomeAssistant, fake_client) -> None:
    """The point of the fix: no manual reload once the console is back."""
    healthy = AsyncMock()
    refused = AsyncMock(side_effect=ConnectionRefusedError(errno.ECONNREFUSED, "Connect call failed"))
    target = "tests.conftest.FakeClient.connect_and_stay_connected"
    with patch(target, refused):
        entry = await _setup(hass)
    assert entry.state is ConfigEntryState.SETUP_RETRY
    with patch(target, healthy):
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=2))
        await hass.async_block_till_done(wait_background_tasks=True)
    assert healthy.await_count == 1
    assert entry.state is ConfigEntryState.LOADED
