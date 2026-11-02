"""Fixtures: a fake AirTouch 5 console with one AC and three zones."""

from pathlib import Path
from types import SimpleNamespace

import custom_components

# The test harness ships its own `custom_components` package; make the fork's
# integration findable through it too.
custom_components.__path__.append(str(Path(__file__).resolve().parents[1] / "custom_components"))

from unittest.mock import patch

from airtouch5py.packets.ac_ability import AcAbility
from airtouch5py.packets.ac_status import AcFanSpeed, AcMode, AcPowerState, AcStatus
from airtouch5py.packets.zone_name import ZoneName
from airtouch5py.packets.zone_status import ControlMethod, ZonePowerState, ZoneStatusZone
import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Load custom_components/airtouch5 instead of the built-in integration."""
    return


def ac_status(**changes) -> AcStatus:
    values = dict(
        ac_power_state=AcPowerState.ON, ac_number=0, ac_mode=AcMode.HEAT,
        ac_fan_speed=AcFanSpeed.MEDIUM, ac_setpoint=22, turbo_active=False,
        bypass_active=False, spill_active=False, timer_set=False,
        temperature=20.7, error_code=0,
    )
    values.update(changes)
    return AcStatus(**values)


def zone_status(number: int, **changes) -> ZoneStatusZone:
    values = dict(
        zone_power_state=ZonePowerState.ON, zone_number=number,
        control_method=ControlMethod.TEMPERATURE_CONTROL, open_percentage=0.8,
        set_point=22, has_sensor=True, temperature=18.2, spill_active=False,
        is_low_battery=False,
    )
    values.update(changes)
    return ZoneStatusZone(**values)


class FakeClient:
    """Stands in for Airtouch5SimpleClient; no network."""

    def __init__(self, host: str) -> None:
        self._client = SimpleNamespace(_writer=None)  # no socket open
        self.ac = [AcAbility(
            ac_number=0, ac_name="AC", start_zone_number=0, zone_count=3,
            supports_mode_cool=True, supports_mode_fan=True, supports_mode_dry=True,
            supports_mode_heat=True, supports_mode_auto=True,
            supports_fan_speed_intelligent_auto=False, supports_fan_speed_turbo=False,
            supports_fan_speed_powerful=False, supports_fan_speed_high=True,
            supports_fan_speed_medium=True, supports_fan_speed_low=True,
            supports_fan_speed_quiet=False, supports_fan_speed_auto=False,
            min_cool_set_point=16, max_cool_set_point=32,
            min_heat_set_point=16, max_heat_set_point=32,
        )]
        self.zones = [ZoneName(0, "Library"), ZoneName(1, "Kitchen"), ZoneName(2, "Hallway")]
        self.latest_ac_status = {0: ac_status()}
        # Zone 2 has no wireless sensor, so it gets no battery entity.
        self.latest_zone_status = {
            0: zone_status(0), 1: zone_status(1), 2: zone_status(2, has_sensor=False),
        }
        self.connection_state_callbacks = []
        self.data_packet_callbacks = []
        self.ac_status_callbacks = []
        self.zone_status_callbacks = []

    async def connect_and_stay_connected(self) -> None:
        return

    async def disconnect(self) -> None:
        return

    async def send_packet(self, packet) -> None:
        return

    def push_ac(self, status: AcStatus) -> None:
        self.latest_ac_status = {status.ac_number: status}
        for cb in list(self.ac_status_callbacks):
            cb(self.latest_ac_status)

    def push_zones(self, *statuses: ZoneStatusZone) -> None:
        self.latest_zone_status = {**self.latest_zone_status, **{z.zone_number: z for z in statuses}}
        for cb in list(self.zone_status_callbacks):
            cb(self.latest_zone_status)


@pytest.fixture
def fake_client():
    """Patch the client the integration creates; yields the instance."""
    created = {}

    def factory(host):
        created["client"] = FakeClient(host)
        return created["client"]

    with patch("custom_components.airtouch5.Airtouch5SimpleClient", side_effect=factory):
        yield created
