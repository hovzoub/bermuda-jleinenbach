"""Test Bermuda device_tracker platform."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.components.device_tracker.const import SourceType
from homeassistant.const import STATE_HOME, STATE_NOT_HOME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockEntityPlatform

from custom_components.bermuda.device_tracker import (
    BermudaDeviceTracker,
    async_setup_entry,
)

from .test_coordinator_methods import _make_coordinator


class TestAsyncSetupEntry:
    """Tests for async_setup_entry function."""

    @pytest.mark.asyncio
    async def test_async_setup_entry_registers_dispatcher(self, hass: HomeAssistant) -> None:
        """Test that async_setup_entry registers a dispatcher listener."""
        mock_coordinator = MagicMock()
        mock_coordinator.devices = {}

        mock_entry = MagicMock()
        mock_entry.runtime_data = MagicMock()
        mock_entry.runtime_data.coordinator = mock_coordinator
        mock_entry.async_on_unload = MagicMock()

        mock_add_devices = MagicMock()

        with patch("custom_components.bermuda.device_tracker.async_dispatcher_connect") as mock_dispatcher:
            await async_setup_entry(hass, mock_entry, mock_add_devices)

        mock_dispatcher.assert_called_once()
        mock_entry.async_on_unload.assert_called_once()


class TestBermudaDeviceTracker:
    """Tests for BermudaDeviceTracker class."""

    def _create_tracker(
        self,
        zone: str = STATE_HOME,
        area_name: str | None = "Living Room",
        area_advert: MagicMock | None = None,
    ) -> BermudaDeviceTracker:
        """Create a BermudaDeviceTracker instance for testing."""
        mock_coordinator = MagicMock()
        mock_coordinator.last_update_success = True

        mock_device = MagicMock()
        mock_device.name = "Test Device"
        mock_device.unique_id = "test_unique_id"
        mock_device.address = "aa:bb:cc:dd:ee:ff"
        mock_device.zone = zone
        mock_device.area_name = area_name
        mock_device.area_advert = area_advert
        mock_coordinator.devices = {"aa:bb:cc:dd:ee:ff": mock_device}

        mock_config_entry = MagicMock()
        mock_config_entry.options = {}

        with (
            patch("custom_components.bermuda.entity.ar.async_get") as mock_ar,
            patch("custom_components.bermuda.entity.dr.async_get") as mock_dr,
        ):
            mock_ar.return_value = MagicMock()
            mock_dr.return_value = MagicMock()

            tracker = object.__new__(BermudaDeviceTracker)
            tracker.coordinator = mock_coordinator
            tracker.config_entry = mock_config_entry
            tracker.address = "aa:bb:cc:dd:ee:ff"
            tracker._device = mock_device
            tracker._lastname = mock_device.name
            tracker.ar = mock_ar.return_value
            tracker.dr = mock_dr.return_value
            tracker.devreg_init_done = False

        return tracker

    def test_tracker_has_correct_attributes(self) -> None:
        """Test that tracker has correct entity attributes."""
        # Create an instance to test attributes (HA metaclass converts class attrs to properties)
        tracker = self._create_tracker()
        assert tracker.should_poll is False
        assert tracker.has_entity_name is True
        assert tracker._attr_translation_key == "tracker"

    def test_unique_id(self) -> None:
        """Test that unique_id is correct."""
        tracker = self._create_tracker()
        assert tracker.unique_id == "test_unique_id"

    def test_state_returns_zone(self) -> None:
        """Test that state returns the device zone."""
        tracker = self._create_tracker(zone=STATE_HOME)
        assert tracker.state == STATE_HOME

    def test_source_type(self) -> None:
        """Test that source_type is BLUETOOTH_LE."""
        tracker = self._create_tracker()
        assert tracker.source_type == SourceType.BLUETOOTH_LE

    def test_icon_when_home(self) -> None:
        """Test icon when device is home."""
        tracker = self._create_tracker(zone=STATE_HOME)
        assert tracker.icon == "mdi:bluetooth-connect"

    def test_icon_when_not_home(self) -> None:
        """Test icon when device is not home."""
        tracker = self._create_tracker(zone="not_home")
        assert tracker.icon == "mdi:bluetooth-off"

    def test_extra_state_attributes_with_advert(self) -> None:
        """Test extra_state_attributes when advert exists."""
        mock_advert = MagicMock()
        mock_advert.name = "Living Room Scanner"
        tracker = self._create_tracker(area_name="Kitchen", area_advert=mock_advert)

        attrs = tracker.extra_state_attributes
        assert attrs["scanner"] == "Living Room Scanner"
        assert attrs["area"] == "Kitchen"

    def test_extra_state_attributes_without_advert(self) -> None:
        """Test extra_state_attributes when no advert."""
        tracker = self._create_tracker(area_name="Kitchen", area_advert=None)

        attrs = tracker.extra_state_attributes
        assert attrs["scanner"] is None
        assert attrs["area"] == "Kitchen"


class TestDeviceNewCallback:
    """Tests for the device_new callback in async_setup_entry."""

    @pytest.mark.asyncio
    async def test_device_new_creates_tracker(self, hass: HomeAssistant) -> None:
        """Test that device_new callback creates device tracker entity."""
        mock_device = MagicMock()
        mock_device.name = "Test Device"
        mock_device.unique_id = "test_unique_id"
        mock_device.address = "aa:bb:cc:dd:ee:ff"
        mock_device.zone = STATE_HOME
        mock_device.area_name = "Living Room"
        mock_device.area_advert = None

        mock_coordinator = MagicMock()
        mock_coordinator.hass = hass
        mock_coordinator.last_update_success = True
        mock_coordinator.devices = {"aa:bb:cc:dd:ee:ff": mock_device}
        mock_coordinator.check_for_duplicate_entities = MagicMock(return_value=None)
        mock_coordinator.device_tracker_created = MagicMock()

        mock_entry = MagicMock()
        mock_entry.runtime_data = MagicMock()
        mock_entry.runtime_data.coordinator = mock_coordinator
        mock_entry.async_on_unload = MagicMock()
        mock_entry.options = {}

        added_entities: list = []
        mock_add_devices = MagicMock(side_effect=lambda entities, _: added_entities.extend(entities))

        with (
            patch("custom_components.bermuda.device_tracker.async_dispatcher_connect") as mock_dispatcher,
            patch("custom_components.bermuda.entity.ar.async_get") as mock_ar,
            patch("custom_components.bermuda.entity.dr.async_get") as mock_dr,
        ):
            mock_ar.return_value = MagicMock()
            mock_dr.return_value = MagicMock()

            await async_setup_entry(hass, mock_entry, mock_add_devices)

            callback_func = mock_dispatcher.call_args[0][2]
            callback_func("aa:bb:cc:dd:ee:ff")

        assert len(added_entities) == 1
        assert isinstance(added_entities[0], BermudaDeviceTracker)
        mock_coordinator.device_tracker_created.assert_called_once_with("aa:bb:cc:dd:ee:ff")

    @pytest.mark.asyncio
    async def test_device_new_handles_duplicate_cleanup(self, hass: HomeAssistant) -> None:
        """Test that device_new handles duplicate entity cleanup."""
        mock_device = MagicMock()
        mock_device.name = "Test Device"
        mock_device.unique_id = "test_unique_id"
        mock_device.address = "aa:bb:cc:dd:ee:ff"
        mock_device.zone = STATE_HOME
        mock_device.area_name = "Living Room"
        mock_device.area_advert = None

        mock_coordinator = MagicMock()
        mock_coordinator.hass = hass
        mock_coordinator.last_update_success = True
        mock_coordinator.devices = {"aa:bb:cc:dd:ee:ff": mock_device}
        mock_coordinator.check_for_duplicate_entities = MagicMock(return_value="old:aa:bb:cc:dd:ee:ff")
        mock_coordinator.cleanup_old_entities_for_device = MagicMock()
        mock_coordinator.device_tracker_created = MagicMock()

        mock_entry = MagicMock()
        mock_entry.runtime_data = MagicMock()
        mock_entry.runtime_data.coordinator = mock_coordinator
        mock_entry.async_on_unload = MagicMock()
        mock_entry.options = {}

        mock_add_devices = MagicMock()

        with (
            patch("custom_components.bermuda.device_tracker.async_dispatcher_connect") as mock_dispatcher,
            patch("custom_components.bermuda.entity.ar.async_get") as mock_ar,
            patch("custom_components.bermuda.entity.dr.async_get") as mock_dr,
        ):
            mock_ar.return_value = MagicMock()
            mock_dr.return_value = MagicMock()

            await async_setup_entry(hass, mock_entry, mock_add_devices)

            callback_func = mock_dispatcher.call_args[0][2]
            callback_func("aa:bb:cc:dd:ee:ff")

        mock_coordinator.cleanup_old_entities_for_device.assert_called_once_with(
            "old:aa:bb:cc:dd:ee:ff", "aa:bb:cc:dd:ee:ff"
        )

    @pytest.mark.asyncio
    async def test_device_new_skips_duplicates(self, hass: HomeAssistant) -> None:
        """Test that device_new skips already-created devices."""
        mock_device = MagicMock()
        mock_device.name = "Test Device"
        mock_device.unique_id = "test_unique_id"
        mock_device.address = "aa:bb:cc:dd:ee:ff"
        mock_device.zone = STATE_HOME
        mock_device.area_name = "Living Room"
        mock_device.area_advert = None

        mock_coordinator = MagicMock()
        mock_coordinator.hass = hass
        mock_coordinator.last_update_success = True
        mock_coordinator.devices = {"aa:bb:cc:dd:ee:ff": mock_device}
        mock_coordinator.check_for_duplicate_entities = MagicMock(return_value=None)
        mock_coordinator.device_tracker_created = MagicMock()

        mock_entry = MagicMock()
        mock_entry.runtime_data = MagicMock()
        mock_entry.runtime_data.coordinator = mock_coordinator
        mock_entry.async_on_unload = MagicMock()
        mock_entry.options = {}

        call_count = 0

        def track_calls(entities, _):
            nonlocal call_count
            call_count += 1

        mock_add_devices = MagicMock(side_effect=track_calls)

        with (
            patch("custom_components.bermuda.device_tracker.async_dispatcher_connect") as mock_dispatcher,
            patch("custom_components.bermuda.entity.ar.async_get") as mock_ar,
            patch("custom_components.bermuda.entity.dr.async_get") as mock_dr,
        ):
            mock_ar.return_value = MagicMock()
            mock_dr.return_value = MagicMock()

            await async_setup_entry(hass, mock_entry, mock_add_devices)

            callback_func = mock_dispatcher.call_args[0][2]
            callback_func("aa:bb:cc:dd:ee:ff")
            callback_func("aa:bb:cc:dd:ee:ff")

        assert call_count == 1


class TestDeviceTrackerIntegration:
    """Integration tests for device_tracker module."""

    def test_module_imports_correctly(self) -> None:
        """Test that the module can be imported without errors."""
        from custom_components.bermuda import device_tracker

        assert hasattr(device_tracker, "async_setup_entry")
        assert hasattr(device_tracker, "BermudaDeviceTracker")

    def test_tracker_inherits_from_correct_classes(self) -> None:
        """Test that BermudaDeviceTracker inherits from required base classes."""
        from homeassistant.components.device_tracker.entity import BaseScannerEntity

        from custom_components.bermuda.entity import BermudaEntity

        assert issubclass(BermudaDeviceTracker, BermudaEntity)
        assert issubclass(BermudaDeviceTracker, BaseScannerEntity)


TRACKER_ADDRESS = "aa:bb:cc:dd:ee:02"
TRACKER_ENTITY_ID = "device_tracker.bermuda_probe"


async def _added_tracker(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch, zones: list[dict[str, object]] | None = None
) -> BermudaDeviceTracker:
    """Add a tracker for a real BermudaDevice to the state machine and the entity registry."""
    assert await async_setup_component(hass, "zone", {"zone": zones or []})
    coordinator = _make_coordinator(hass)
    coordinator.last_update_success = True
    # The lightweight test coordinator skips DataUpdateCoordinator.__init__.
    monkeypatch.setattr(coordinator, "async_add_listener", MagicMock(return_value=lambda: None))
    device = coordinator._get_or_create_device(TRACKER_ADDRESS)
    device.zone = STATE_HOME
    tracker = BermudaDeviceTracker(coordinator, SimpleNamespace(options={}), TRACKER_ADDRESS)  # type: ignore[arg-type]
    tracker.entity_id = TRACKER_ENTITY_ID
    platform = MockEntityPlatform(hass, domain="device_tracker", platform_name="bermuda")
    await platform.async_add_entities([tracker])
    await hass.async_block_till_done()
    return tracker


class TestTrackerOnBaseScannerEntity:
    """The tracker behaves like a Home Assistant scanner entity (in_zones, associated_zone)."""

    async def test_in_zones_follows_home_state(self, hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch) -> None:
        """At home the tracker lists zone.home in in_zones, away it lists nothing."""
        tracker = await _added_tracker(hass, monkeypatch)

        state = hass.states.get(TRACKER_ENTITY_ID)
        assert state is not None
        assert state.state == STATE_HOME
        assert state.attributes["in_zones"] == ["zone.home"]

        tracker._device.zone = STATE_NOT_HOME
        tracker.async_write_ha_state()
        state = hass.states.get(TRACKER_ENTITY_ID)
        assert state is not None
        assert state.state == STATE_NOT_HOME
        assert state.attributes["in_zones"] == []

    async def test_in_zones_includes_enclosing_zone(self, hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch) -> None:
        """A zone that encloses zone.home is listed after it."""
        await _added_tracker(
            hass,
            monkeypatch,
            [{"name": "Big", "latitude": hass.config.latitude, "longitude": hass.config.longitude, "radius": 100000}],
        )

        state = hass.states.get(TRACKER_ENTITY_ID)
        assert state is not None
        assert state.attributes["in_zones"] == ["zone.home", "zone.big"]

    async def test_registry_identity(self, hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch) -> None:
        """The registry entry keeps no category, the tracker translation key and the device unique_id."""
        tracker = await _added_tracker(hass, monkeypatch)

        entry = er.async_get(hass).async_get(TRACKER_ENTITY_ID)
        assert entry is not None
        assert entry.entity_category is None
        assert entry.translation_key == "tracker"
        assert entry.unique_id == tracker._device.unique_id

    async def test_source_type_is_bluetooth_le(self, hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch) -> None:
        """The state reports Bluetooth LE as source type."""
        await _added_tracker(hass, monkeypatch)

        state = hass.states.get(TRACKER_ENTITY_ID)
        assert state is not None
        assert state.attributes["source_type"] == SourceType.BLUETOOTH_LE

    async def test_associated_zone_sets_state(self, hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch) -> None:
        """With an associated zone in the registry options, home means that zone."""
        await _added_tracker(
            hass,
            monkeypatch,
            [{"name": "Work", "latitude": 52.0, "longitude": 13.0, "radius": 100}],
        )

        er.async_get(hass).async_update_entity_options(
            TRACKER_ENTITY_ID, "device_tracker", {"associated_zone": "zone.work"}
        )
        await hass.async_block_till_done()

        state = hass.states.get(TRACKER_ENTITY_ID)
        assert state is not None
        assert state.state == "Work"
        assert state.attributes["in_zones"] == ["zone.work"]

    async def test_recorder_excludes_only_scanner_and_area(
        self, hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The recorder skips scanner and area but keeps in_zones and source_type."""
        await _added_tracker(hass, monkeypatch)

        state = hass.states.get(TRACKER_ENTITY_ID)
        assert state is not None
        assert state.state_info is not None
        assert state.state_info["unrecorded_attributes"] == frozenset({"scanner", "area"})
